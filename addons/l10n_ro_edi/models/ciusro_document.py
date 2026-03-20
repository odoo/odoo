from odoo import api, fields, models


class L10n_Ro_EdiDocument(models.Model):
    _name = 'l10n_ro_edi.document'
    _description = "Document object for tracking CIUS-RO XML sent to E-Factura"
    _order = 'datetime DESC, id DESC'

    invoice_id = fields.Many2one(comodel_name='account.move', required=True, readonly=True)
    state = fields.Selection(
        selection=[
            ('invoice_sent', 'Sent'),
            ('invoice_refused', 'Error'),
            ('invoice_validated', 'Validated'),
        ],
        string='E-Factura Status',
        readonly=True,
        required=True,
        help="""Sent -> Successfully sent to the SPV, waiting for validation.
                Validated -> Sent & validated by the SPV.
                Refused -> Sent & refused by the SPV.
        """,
    )
    datetime = fields.Datetime(default=fields.Datetime.now, required=True, readonly=True)
    message = fields.Char(readonly=True)
    key_signature = fields.Char(readonly=True)   # Received from a successful response: to be saved for government purposes
    key_certificate = fields.Char(readonly=True)  # Received from a successful response: to be saved for government purposes
    key_download = fields.Char(string="Document download key", readonly=True)
    attachment = fields.Binary(readonly=True)

    # Technical fields
    show_fetch_status_button = fields.Boolean(compute="_compute_show_fetch_status_button")

    @api.depends('state', 'invoice_id.l10n_ro_edi_state')
    def _compute_show_fetch_status_button(self):
        for document in self:
            document.show_fetch_status_button = (document.state == 'invoice_sent' and document.invoice_id.l10n_ro_edi_state == 'invoice_sent')

    def action_l10n_ro_edi_fetch_status(self):
        """ Fetch the latest response from E-Factura about the XML sent """
        self.ensure_one()
        # Do the batch fetch process on a single invoice/document
        self.invoice_id._l10n_ro_edi_fetch_invoice_sent_documents()

    def action_l10n_ro_edi_download_attachment(self):
        """ Download the sent attachment in case if no status have been received from ANAF.
            Otherwise, download the received successful signature XML file from E-Factura.
        """
        self.ensure_one()
        attachment_sudo = self.env['ir.attachment'].sudo().search([
            ('res_model', '=', self._name),
            ('res_field', '=', 'attachment'),
            ('res_id', '=', self.id),
        ])
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment_sudo.id}?download=true',
        }
