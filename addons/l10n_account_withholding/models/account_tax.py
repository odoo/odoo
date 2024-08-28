# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    # ------------------
    # Fields declaration
    # ------------------

    type_tax_use = fields.Selection(
        selection_add=[
            ('sales_wth', "Sales Withholding"),
            ('purchases_wth', "Purchases Withholding"),
        ],
        ondelete={'sales_wth': 'set default', 'purchases_wth': 'set default'}
    )
    l10n_account_withholding_sequence_id = fields.Many2one(
        string='Withholding Sequence',
        help='Label displayed on Journal Items and Payment Receipts.',
        comodel_name='ir.sequence',
        copy=False,
        check_company=True,
    )
