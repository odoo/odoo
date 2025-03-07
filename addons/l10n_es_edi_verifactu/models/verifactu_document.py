from odoo import _, api, fields, models
from odoo.exceptions import UserError


class L10nEsEdiVerifactuDocument(models.Model):
    """Veri*Factu Document
    It represents an internal record / event in the Veri*Factu XML format as specified by the AEAT.
    It i.e. ...
      * stores the XML we will send to the AEAT
      * is eventually send to the AEAT via a "Veri*Factu Request" ('l10n_es_edi_verifactu.request') of type "Batch"
      * stores information extracted from the associated "Veri*Factu Request" about the received response

    Note that (succesfully generated) Documents can not be deleted.
    This is since the Documents form a chain (in generation order) by including a reference to the preceding document.
    The chain also includes documents that are (/ possibly will be) rejected by the AEAT.
    The correct chaining is handled by function `l10n_es_edi_verifactu_mark_for_next_batch`  of model / mixin
    "Veri*Factu Record Mixin" / 'l10n_es_edi_verifactu.record_mixin'.

    Also see the docstring of the "Veri*Factu Record Mixin" for more details about the general flow.
    """
    _name = 'l10n_es_edi_verifactu.document'
    _description = "Veri*Factu Document"
    _order = 'response_time DESC NULLS FIRST, create_date DESC, id DESC'

    company_id = fields.Many2one(
        string="Company",
        comodel_name='res.company',
        required=True,
        readonly=True,
    )
    # `res_model` and `res_id` are used to link the object the document was created from
    res_model = fields.Char(
        string="Origin Model",
        required=True,
        readonly=True,
    )
    res_id = fields.Many2oneReference(
        string="Origin ID",
        model_field='res_model',
        required=True,
        readonly=True,
    )
    record_identifier = fields.Json(
        string="Veri*Factu Record Identifier",
        help="Technical field containing the values used to identify records in the Veri*Factu system.",
        readonly=True,
    )
    document_type = fields.Selection(
        string='Document Type',
        selection=[
            ('submission', 'Submission'),
            ('cancellation', 'Cancellation'),
        ],
        readonly=True,
        required = True,
    )
    xml_attachment_id = fields.Many2one(
        string="XML Attachment",
        comodel_name='ir.attachment',
        readonly=True,
    )
    xml_attachment_filename = fields.Char(
        string='XML filename',
        compute='_compute_xml_attachment_filename',
    )
    # To use the 'binary' widget in the form view to download the attachment
    xml_attachment_base64 = fields.Binary(
        string="XML Attachment (Base64)",
        related='xml_attachment_id.datas',
    )
    state = fields.Selection(
        string='Status',
        selection=[
            ('creating_failed', 'Creating Failed'),
            ('sending_failed', 'Sending Failed'),
            ('parsing_failed', 'Error while Parsing the Response'),
            ('rejected', 'Rejected'),
            ('registered_with_errors', 'Registered with Errors'),
            ('accepted', 'Accepted'),
        ],
        compute='_compute_state_and_response_time',
        store=True,
        help="""- Creating Failed: The record could not be created.
                - Sending Failed: Tried to send to the AEAT but failed
                - Parsing Failed: There was an error while parsing the response from he AEAT
                - Rejected: Successfully sent to the AEAT, but it was rejected during validation
                - Registered with Errors: Registered at the AEAT, but the AEAT has some issues with the sent record
                - Accepted: Registered by the AEAT without errors""",
        copy=False,
        readonly=True,
    )
    request_id = fields.Many2one(
        string="Veri*Factu Document",
        comodel_name='l10n_es_edi_verifactu.request',
        help="The document in which the record is sent to the AEAT.",
        copy=False,
        readonly=True,
    )
    response_time = fields.Datetime(
        string="Time of Response",
        compute='_compute_state_and_response_time',
        store=True,
        help="The date and time on which we received the response (or tried to send in case of failure).",
        copy=False,
        readonly=True,
    )
    errors = fields.Html(
        string="Errors",
        compute='_compute_errors',
        store=True,  # we need it to store the errors from the XML generation; TODO: issue for translation
        copy=False,
        readonly=True,
    )

    @api.depends('document_type')
    def _compute_display_name(self):
        for document in self:
            document.display_name = _("Verifactu Document %s", document.id)

    @api.depends('document_type')
    def _compute_xml_attachment_filename(self):
        for document in self:
            document_type = 'annulacion' if document.document_type == 'cancellation' else 'alta'
            name = f"verifactu_registro_{document.id}_{document_type}.xml"
            document.xml_attachment_filename = name

    @api.depends('record_identifier', 'request_id', 'request_id.response_info', 'xml_attachment_id')
    def _compute_state_and_response_time(self):
        for document in self:
            if not document.xml_attachment_id:
                document.state = 'creating_failed'
                document.response_time = False
                continue

            request = document.request_id
            if not request or not request.response_info:
                document.state = False
                document.response_time = False
                continue

            record_response_info = request._get_record_response_info(document.record_identifier)
            document.state = record_response_info['state']
            document.response_time = request.response_info['response_time']

    @api.depends('record_identifier', 'request_id', 'request_id.response_info', 'xml_attachment_id')
    def _compute_errors(self):
        for document in self:
            if not document.xml_attachment_id:
                document.errors = document.errors
                continue

            request = document.request_id
            if not request or not request.response_info:
                document.errors = False
                continue

            errors = False
            record_response_info = request._get_record_response_info(document.record_identifier)
            state = record_response_info['state']
            response_errors = record_response_info['errors']
            info_level = record_response_info['level']  # taken for the whole request or just this document
            if response_errors:
                if state == 'parsing_failed':
                    error_title = _("There was an issue parsing the reponse from the AEAT")
                elif info_level == 'document':
                    error_title = _("There was an issue sending the batch document to the AEAT")
                else:
                    error_title = _("The Veri*Factu record contains the following errors according to the AEAT")
                error = {
                    'error_title': error_title,
                    'errors': response_errors,
                }
                errors = self.env['account.move.send']._format_error_html(error)

            document.errors = errors

    @api.ondelete(at_uninstall=False)
    def _never_unlink_chained_documents(self):
        for document in self:
            if document.state != 'creating_failed':
                raise UserError(_("You cannot delete Veri*Factu records that are part of the chain of all Veri*Factu records."))

    def _create_batch_xml(self):
        # For the cron we specifically set the `self.env.company`
        document_xmls = [rd.xml_attachment_id.raw.decode() for rd in self]
        batch_xml, batch_errors = self.env['l10n_es_edi_verifactu.xml']._batch_record_xmls(document_xmls)

        if batch_errors:
            message = self.env['account.move.send']._format_error_html({
                'error_title': _("Errors during the batching of the Veri*Factu documents."),
                'errors': batch_errors,
            })
            self.errors = message

        return batch_xml, batch_errors
