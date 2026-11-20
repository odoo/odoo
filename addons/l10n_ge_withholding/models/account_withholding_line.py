from odoo import api, fields, models
from odoo.exceptions import UserError


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

    @api.depends('tax_id.l10n_ge_is_gross')
    def _compute_original_amounts(self):
        super()._compute_original_amounts()
        # A base typed by hand is the gross base, as on the lines coming from a bill: don't gross it up again.
        for line in self.filtered(lambda line: not line.source_currency_id and line.tax_id.l10n_ge_is_gross):
            line_curr = line.comodel_currency_id or line.comodel_company_currency_id
            line.original_tax_amount = line_curr.round(line.original_base_amount * abs(line.tax_id.amount) / 100)

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

    def _prepare_withholding_amls_create_values(self):
        aml_create_values_list = super()._prepare_withholding_amls_create_values()
        company = self.company_id
        gross_cost_values_list = []
        for vals in aml_create_values_list:
            tax = self.env['account.tax.repartition.line'].browse(vals.get('tax_repartition_line_id')).tax_id
            if tax.l10n_ge_is_gross:
                # The company bears the gross withholding: its cost balances the withheld tax, so the vendor is paid in full.
                if not company.l10n_ge_withholding_gross_account_id:
                    raise UserError(self.env._("Set the Gross Withholding Cost account in the Invoicing settings to pay gross withholding taxes."))
                gross_cost_values_list.append({
                    'name': self.env._("WH Gross Cost: %(name)s", name=tax.name),
                    'account_id': company.l10n_ge_withholding_gross_account_id.id,
                    'partner_id': vals['partner_id'],
                    'currency_id': vals['currency_id'],
                    'amount_currency': -vals['amount_currency'],
                    'balance': -vals['balance'],
                })
        return aml_create_values_list + gross_cost_values_list
