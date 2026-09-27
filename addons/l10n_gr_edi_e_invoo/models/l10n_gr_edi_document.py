from urllib.parse import urlsplit

from odoo import fields, models


class GreeceEDIDocument(models.Model):
    _inherit = 'l10n_gr_edi.document'

    state = fields.Selection(
        selection_add=[('invoice_pending', "Invoice submission pending")],
        ondelete={'invoice_pending': 'cascade'},
    )

    mydata_uid = fields.Char(string='myDATA UID', copy=False)
    mydata_authentication_code = fields.Char(string='myDATA Authentication Code', copy=False)

    provider_uid = fields.Char(copy=False)
    provider_invoice_identifier = fields.Char(string='Invoice Identifier', copy=False)
    provider_qr_url = fields.Char(string='Provider QR URL', copy=False)

    # pdf upload is tracked separately because the invoice is already issued at this stage
    provider_pdf_state = fields.Selection(
        selection=[
            ('pending', "Pending"),
            ('sent', "Sent"),
            ('error', "Failed"),
        ],
        string='Final PDF Status',
        copy=False,
    )
    provider_pdf_error = fields.Text(copy=False)

    def _l10n_gr_edi_get_provider_parent_token(self):
        self.ensure_one()
        path = urlsplit(self.provider_qr_url or '').path.rstrip('/')
        return path.rsplit('/', 1)[-1] if path else False
