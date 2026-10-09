from odoo import fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_ge_wht_category_ids = fields.Many2many(
        comodel_name='l10n_ge.wht.category',
        string="Withholding Tax Categories",
        help="Income recipient categories this withholding tax applies to. When a contact has categories,"
        " only taxes sharing one of them are offered on its bills and payments.",
    )
