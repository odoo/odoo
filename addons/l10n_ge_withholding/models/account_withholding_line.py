from odoo import api, fields, models


class AccountWithholdingLine(models.AbstractModel):
    _inherit = 'account.withholding.line'

    tax_id = fields.Many2one(
        domain="[('type_tax_use', '=', type_tax_use), ('is_withholding_tax', '=', True)]"
        " + (l10n_ge_tax_id_domain or [])",
    )
    l10n_ge_treaty_exempt_amount = fields.Monetary(
        currency_field='comodel_currency_id',
        string="Withheld Treaty Exempt",
        help="Amount an international tax treaty exempts from withholding. Informational only: it"
        " changes neither the withheld amount nor the journal entry amounts.",
    )
    l10n_ge_tax_id_domain = fields.Json(
        string="Withholding tax category domain",
        help="Restricts the withholding taxes to the categories of the recipient, when it has some.",
        compute='_compute_l10n_ge_tax_id_domain',
    )

    @api.depends('country_code')
    def _compute_l10n_ge_tax_id_domain(self):
        for line in self:
            categories = line._get_comodel_partner().l10n_ge_wht_category_ids
            if line.country_code == 'GE' and categories:
                line.l10n_ge_tax_id_domain = [('l10n_ge_wht_category_ids', 'in', categories.ids)]
            else:
                line.l10n_ge_tax_id_domain = []

    def _l10n_ge_get_treaty_exempt_amounts(self):
        """ Return the (tax line grouping key, treaty exempt amount) of each line, the amount in company currency. """
        AccountTax = self.env['account.tax']
        treaty_amounts = []
        for line in self.filtered(lambda line: line.tax_id.country_code == 'GE'):
            company = line.company_id
            base_line = line._prepare_base_line_for_taxes_computation()
            AccountTax._add_tax_details_in_base_line(base_line, company)
            AccountTax._round_base_lines_tax_details([base_line], company)
            AccountTax._add_accounting_data_in_base_lines_tax_details([base_line], company)
            rate = base_line['rate']
            amount = company.currency_id.round(line.l10n_ge_treaty_exempt_amount / rate) if rate else 0.0
            amount *= base_line['sign']
            for tax_data in base_line['tax_details']['taxes_data']:
                if tax_rep_data := tax_data['tax_reps_data'][:1]:
                    # The tax grids are left out: account._sync_tax_lines may wipe them on the tax line when the entry is reset to draft.
                    grouping_key = {field: value for field, value in tax_rep_data[0]['grouping_key'].items() if field not in ('partner_id', 'tax_tag_ids') and not field.startswith('__')}
                    treaty_amounts.append((grouping_key, amount))
        return treaty_amounts
