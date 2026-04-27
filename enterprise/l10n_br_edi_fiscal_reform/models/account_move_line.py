# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    l10n_br_cbs_ibs_deduction = fields.Monetary(
        string='CBS/IBS Credit',
        currency_field='currency_id',
        help='Brazil: Deduction value to reduce the CBS/IBS taxable base in outbound invoices for certain operations.',
    )
