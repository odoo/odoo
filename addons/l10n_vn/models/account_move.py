from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_vn_e_invoice_number = fields.Char(
        string="eInvoice Number",
        copy=False,
        help="Electronic Invoicing number.",
    )
