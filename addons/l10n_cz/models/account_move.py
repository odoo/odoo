# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    taxable_supply_date = fields.Date(string="Taxable Supply Date", default=fields.Date.context_today, required=True)

    # User can optionally select a scheme code
    l10n_cz_scheme_code = fields.Selection(
        selection=[
            ('0', '0 - Standard VAT regime'),
            ('1', '1 - Section 89 of VAT Act special scheme for a travel service'),
            ('2', '2 - Section 90 of VAT Act margin scheme'),
        ],
        string='Special scheme code',
        help='Code indicating special scheme, needed for VAT control report.',
        default='0',
        readonly=True,
    )
