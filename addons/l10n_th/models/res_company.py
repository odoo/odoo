from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_th_is_vat_registered = fields.Boolean(
        string="Thailand: VAT Registered",
        help="Check this to enable issuing Tax Invoices. Otherwise, only standard invoices or receipts can be issued.",
    )
