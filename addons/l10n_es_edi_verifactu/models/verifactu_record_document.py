from odoo import _, api, fields, models
from odoo.exceptions import UserError


class L10nEsEdiVerifactuRecordDocument(models.Model):
    """Veri*Factu Record Document
    It represents an internal record / event in the Veri*Factu XML format as specified by the AEAT.
    It i.e.:
      * stores the XML we send
      * is eventually associated with a "Veri*Factu Document" ('l10n_es_edi_verifactu.document') of type "Batch" to send it to the AEAT
      * stores information extracted from the associated "Veri*Factu Document" about the received response"""
    _name = 'l10n_es_edi_verifactu.record_document'
    _description = "Veri*Factu Record Document"
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
    record_type = fields.Selection(
        string='Record Type',
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
    # To use the binary widget in the form view to download the attachment
    xml_attachment_base64 = fields.Binary(
        string="XML Attachment (Base64)",
        related='xml_attachment_id.datas'
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
        compute='_compute_state',
        store=True,
        help="""- Creating Failed: The record could not be created.
                - Sending Failed: Tried to send to the AEAT but failed
                - Rejected: Successfully sent to the AEAT, but it was rejected during validation
                - Registered with Errors: Registered at the AEAT, but the AEAT has some issues with the sent record
                - Accepted: Registered by the AEAT without errors
                - Cancelled: Registered by the AEAT as cancelled""",
        copy=False,
        readonly=True,
    )
    document_id = fields.Many2one(
        string="Veri*Factu Document",
        comodel_name='l10n_es_edi_verifactu.document',
        help="The document in which the record is sent to the AEAT.",
        copy=False,
        readonly=True,
    )
    response_time = fields.Datetime(
        string="Time of Response",
        related='document_id.response_time',
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

    @api.depends('record_type')
    def _compute_display_name(self):
        for record_document in self:
            record_document.display_name = _("Verifactu Record %s", record_document.id)

    @api.depends('record_type')
    def _compute_xml_attachment_filename(self):
        for record_document in self:
            record_type = 'annulacion' if record_document.record_type == 'cancellation' else 'alta'
            name = f"verifactu_registro_{record_document.id}_{record_type}.xml"
            record_document.xml_attachment_filename = name

    @api.depends('record_identifier', 'document_id', 'document_id.response_info', 'xml_attachment_id')
    def _compute_state(self):
        for record in self:
            if not record.xml_attachment_id:
                record.state = 'creating_failed'
                continue

            document = record.document_id
            if not document or not document.response_info:
                record.state = False
                continue

            record_response_info = document._get_record_response_info(record.record_identifier)
            record.state = record_response_info['state']

    @api.depends('record_identifier', 'document_id', 'document_id.response_info', 'xml_attachment_id')
    def _compute_errors(self):
        for record in self:
            if not record.xml_attachment_id:
                record.errors = record.errors
                continue

            document = record.document_id
            if not document or not document.response_info:
                record.errors = False
                continue

            errors = False
            record_response_info = document._get_record_response_info(record.record_identifier)
            state = record_response_info['state']
            response_errors = record_response_info['errors']
            info_level = record_response_info['level']
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

            record.errors = errors

    @api.ondelete(at_uninstall=False)
    def _never_unlink_chained_record_documents(self):
        for record_document in self:
            if record_document.state != 'creating_failed':
                raise UserError(_("You cannot delete Veri*Factu records that are part of the chain of all Veri*Factu records."))

    def _create_batch_xml(self):
        # For the cron we specifically set the `self.env.company`
        record_document_xmls = [rd.xml_attachment_id.raw.decode() for rd in self]
        batch_xml, batch_errors = self.env['l10n_es_edi_verifactu.xml']._batch_record_xmls(record_document_xmls)

        if batch_errors:
            message = self.env['account.move.send']._format_error_html({
                'error_title': _("Errors during the batching of the Veri*Factu document records."),
                'errors': batch_errors,
            })
            self.errors = message

        return batch_xml, batch_errors

    def _create_batch_document(self):
        # For the cron we specifically set the `self.env.company`
        batch_xml, batch_errors = self.with_company(self.env.company)._create_batch_xml()
        if batch_errors:
            None

        return self.env['l10n_es_edi_verifactu.document']._create_batch_document(batch_xml, self)
