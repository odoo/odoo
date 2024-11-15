from odoo import _, api, fields, models


class L10nEsEdiVerifactuRecordDocument(models.Model):
    _name = 'l10n_es_edi_verifactu.record_document'
    _description = "Record object representing a Veri*Factu XML"
    _order = 'response_time DESC, create_date DESC, id DESC'

    company_id = fields.Many2one(
        comodel_name='res.company',
        required=True,
    )
    # `res_model` and `res_id` are used to link the object the document was created from
    res_model = fields.Char(
        string="Origin Model",
        required=True,
    )
    res_id = fields.Integer(
        string="Origin ID",
        required=True
    )
    document_id = fields.Many2one(
        comodel_name='l10n_es_edi_verifactu.document',
        string="Veri*Factu Document",
        help="The document in which the record is sent to the AEAT.",
        copy=False,
        readonly=True,
    )
    record_identifier = fields.Json(
        string="Veri*Factu Record Identifier",
        help="Technical field containing the values used to identify records in the Veri*Factu system.",
    )
    xml_attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="XML Attachment",
        copy=False,
        readonly=True,
    )
    state = fields.Selection(
        selection=[
            ('creating_failed', 'Creating Failed'),
            ('sending_failed', 'Sending Failed'),
            ('registered_with_errors', 'Registered with Errors'),
            ('accepted', 'Accepted'),
            ('rejected', 'Rejected'),
        ],
        compute='_compute_state_related_fields',
        store=True,
        help="""- Creating Failed: The record could not be created.
                - Sending Failed: Tried to send to the AEAT but failed
                - Rejected: Successfully sent to the AEAT, but it was rejected during validation
                - Registered with Errors: Registered at the AEAT, but the AEAT has some issues with the sent record
                - Accepted: Registered by the AEAT without errors
                - Cancelled: Registered by the AEAT as cancelled""",
        string='Status',
        copy=False,
    )
    response_time = fields.Datetime(
        string="Time of Response",
        related='document_id.response_time',
        store=True,
        help="The date and time on which we received the response (or tried to send in case of failure).",
        copy=False,
    )
    errors = fields.Html(
        string="Errors",
        copy=False,
        compute='_compute_state_related_fields',
        store=True,
    )

    @api.depends('record_identifier', 'document_id', 'document_id.response_info', 'xml_attachment_id')
    def _compute_state_related_fields(self):
        for record in self:
            response_info = record.document_id.response_info
            state = False
            errors = False
            if not record.xml_attachment_id:
                state = 'creating_failed'
                errors = record.errors
            elif response_info:
                record_key = self.env['l10n_es_edi_verifactu.document']._get_record_key(record.record_identifier)
                record_response_info = response_info.get('record_info',{}).get(record_key, {})
                state = record_response_info.get('state', False)
                response_errors = record_response_info.get('errors', False)
                # TODO: case record_key not found in record_info ⇝ also an error
                if response_errors:
                    error = {
                        'error_title': _("The Veri*Factu record contains the following errors according to the AEAT."),
                        'errors': response_errors,
                    }
                    errors = self.env['account.move.send']._format_error_html(error)
            record.state = state
            record.errors = errors

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
            return None, batch_errors

        return batch_xml, batch_errors
