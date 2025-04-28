from odoo import api, fields, models


class L10n_Ro_EdiDocument(models.Model):
    _name = 'l10n_ro_edi.document'
    _description = "Document object for tracking CIUS-RO XML sent to E-Factura"
    _order = 'datetime DESC, id DESC'

    invoice_id = fields.Many2one(comodel_name='account.move', required=True, readonly=True)
    state = fields.Selection(
        selection=[
            ('invoice_sent', 'Sent'),
            ('invoice_sending_failed', 'Error'),
            ('invoice_validated', 'Validated'),
        ],
        string='E-Factura Status',
        readonly=True,
        required=True,
        help="""Sent -> Successfully sent to the SPV, waiting for validation.
                Validated -> Sent & validated by the SPV.
                Error -> Sending error or validation error from the SPV.""",
    )
    datetime = fields.Datetime(default=fields.Datetime.now, required=True, readonly=True)
    message = fields.Char(readonly=True)
    key_signature = fields.Char(readonly=True)   # Received from a successful response: to be saved for government purposes
    key_certificate = fields.Char(readonly=True)  # Received from a successful response: to be saved for government purposes
    key_download = fields.Char(string="Document download key", readonly=True)
    attachment = fields.Binary(readonly=True)

    @api.model
    def _l10n_ro_edi_create_document_invoice_sent(self, invoice, attachment_raw):
        """ Shorthand for creating a ``l10n_ro_edi.document`` of state ``invoice_sent``.

        :param invoice: an ``account.move`` object, the invoice to link the document to
        :param attachment_raw: <bytes>, the document data
        :return: ``l10n_ro_edi.document`` object """
        self.env['l10n_ro_edi.document'].sudo().create({
            'invoice_id': invoice.id,
            'state': 'invoice_sent',
            'attachment': attachment_raw,
        })

    @api.model
    def _l10n_ro_edi_create_document_invoice_sending_failed(self, invoice, error):
        """ Shorthand for creating a ``l10n_ro_edi.document`` of state ``invoice_sending_failed``.
        The ``attachment_raw`` and ``key_loading`` dictionary values is optional in case the error is from pre_send.

        :param invoice: an ``account.move`` object, the invoice to link the document to
        :param error: <str>, the error message
        :return: ``l10n_ro_edi.document`` object """
        self.env['l10n_ro_edi.document'].sudo().create({
            'invoice_id': invoice.id,
            'state': 'invoice_sending_failed',
            'message': error,
        })

    @api.model
    def _l10n_ro_edi_create_document_invoice_validated(self, invoice, key_download, key_signature, key_certificate, attachment_raw):
        """ Shorthand for creating a ``l10n_ro_edi.document`` of state `invoice_validated`.
        The created attachment are saved on both the document and on the invoice.

        :param invoice: an ``account.move`` object, the invoice to link the document to
        :param key_download: <str>, the id to use to download the ZIP containing the document and signature
        :param key_signature: <str>, the document signature
        :param key_certificate: <str>, the certificate used to verify the signature
        :param attachment_raw: <bytes>, the document data
        :return: ``l10n_ro_edi.document`` object """
        self.env['l10n_ro_edi.document'].sudo().create({
            'invoice_id': invoice.id,
            'state': 'invoice_validated',
            'key_signature': key_signature,
            'key_certificate': key_certificate,
            'attachment': attachment_raw,
        })

    def action_l10n_ro_edi_fetch_status(self):
        """ Fetch the latest response from E-Factura about the XML sent """
        self.ensure_one()
        # Do the batch fetch process on a single invoice/document
        self.invoice_id._l10n_ro_edi_fetch_invoice_sent_documents()

    def action_l10n_ro_edi_download_signature(self):
        """ Download the received successful signature XML file from E-Factura """
        self.ensure_one()
        attachment = self.env['ir.attachment'].sudo().search([
            ('res_model', '=', self._name),
            ('res_field', '=', 'attachment'),
            ('res_id', '=', self.id),
        ])
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
        }
