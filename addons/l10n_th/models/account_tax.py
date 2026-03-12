# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_th_income_tax_type = fields.Selection(
        string="Income Tax Type",
        selection=[
            ('service', '40 (2) - Services'),
            ('commission', '40 (2) - Commission / Brokerage'),
            ('royalties', '40 (3) - Royalties'),
            ('interest', '40 (4) a - Interest'),
            ('dividend', '40 (4) b - Dividend'),
            ('rentals', '40 (5) - Rentals'),
            ('prof_fees', '40 (6) - Professional fees'),
            ('contract', '40 (7) - Contract'),
            ('transportation', '40 (8) - Transportation'),
            ('advertising', '40 (8) - Advertising'),
            ('insurance', '40 (8) - Non-life insurance'),
            ('public_actor', '40 (8) - Public Actor'),
            ('prize', '40 (8) - Prize'),
            ('hire_of_work', '40 (8) - Hire of Work'),
            ('others', 'Others'),
            ('na', 'Not Applicable'),
        ],
        help="The income type on 50 Tawi. Select 'Not Applicable' to exclude from 50 Tawi.",
    )
    l10n_th_income_tax_type_others = fields.Char(
        string="Other Type",
        help="Specific income type to display on 50 Tawi.",
    )

    # We reset the values of these fields when they are no longer visible to avoid blocking issue or storing irrelevant data.

    @api.onchange('is_withholding_tax_on_payment', 'type_tax_use', 'country_code')
    def _onchange_l10n_th_income_tax_type_dependencies(self):
        for tax in self:
            if not tax.is_withholding_tax_on_payment or tax.type_tax_use != 'purchase' or tax.country_code != 'TH':
                tax.l10n_th_income_tax_type = False

    @api.onchange('l10n_th_income_tax_type')
    def _onchange_l10n_th_income_tax_type(self):
        for tax in self:
            if tax.l10n_th_income_tax_type != 'others':
                tax.l10n_th_income_tax_type_others = False
