from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_ge_wht_category_ids = fields.Many2many(
        comodel_name='l10n_ge.wht.category',
        string="Withholding Tax Categories",
        help="Income recipient categories this withholding tax applies to. When a contact has categories,"
        " only taxes sharing one of them are offered on its bills and payments.",
    )
    l10n_ge_is_gross = fields.Boolean(
        string="Gross",
        help="The company bears this withholding tax on top of the payment: the vendor receives the full amount.",
    )
    l10n_ge_is_gross_locked = fields.Boolean(compute='_compute_l10n_ge_is_gross_locked')

    @api.onchange('is_withholding_tax')
    def _onchange_is_withholding_tax(self):
        super()._onchange_is_withholding_tax()
        if not self.is_withholding_tax:
            self.l10n_ge_is_gross = False

    @api.constrains('l10n_ge_is_gross', 'is_withholding_tax', 'type_tax_use', 'amount_type', 'amount', 'price_include_override', 'country_id')
    def _check_l10n_ge_is_gross(self):
        for tax in self.filtered('l10n_ge_is_gross'):
            if tax.country_code != 'GE' or not tax.is_withholding_tax or tax.type_tax_use != 'purchase' or tax.amount_type != 'percent' or tax.price_include or not -100 < tax.amount < 0:
                raise ValidationError(self.env._("Gross is only available on Georgian purchase withholding taxes computed as a percentage."))

    def _compute_l10n_ge_is_gross_locked(self):
        ge_taxes = self.filtered(lambda tax: tax.country_code == 'GE')
        used_taxes = set(ge_taxes.sudo().search([('id', 'in', ge_taxes.ids), ('account_move_line_ids.parent_state', '=', 'posted')]))
        for tax in self:
            tax.l10n_ge_is_gross_locked = tax._origin in used_taxes

    def write(self, vals):
        if 'l10n_ge_is_gross' in vals:
            changed_taxes = self.filtered(lambda tax: tax.country_code == 'GE' and tax.l10n_ge_is_gross != bool(vals['l10n_ge_is_gross']))
            if any(changed_taxes.mapped('l10n_ge_is_gross_locked')):
                raise UserError(self.env._("You cannot change Gross on a tax used on posted bills. Create a new withholding tax instead."))
        return super().write(vals)

    @api.model
    def _add_tax_details_in_base_line(self, base_line, company, rounding_method=None):
        super()._add_tax_details_in_base_line(base_line, company, rounding_method=rounding_method)
        if not base_line.get('calculate_withholding_taxes') or base_line.get('l10n_ge_is_gross_base'):
            return
        rounding_method = rounding_method or company.tax_calculation_rounding_method
        currency = base_line['currency_id']
        rate = base_line['rate']
        tax_details = base_line['tax_details']

        def round_amount(amount, currency):
            return currency.round(amount) if rounding_method == 'round_per_line' else amount

        def to_company_currency(amount_currency):
            # As in account.tax._add_tax_details_in_base_line.
            return round_amount(amount_currency / rate if rate else 0.0, company.currency_id)

        for tax_data in tax_details['taxes_data']:
            tax = tax_data['tax']
            if not tax.l10n_ge_is_gross:
                continue
            # Computed from the grossed-up base, not by scaling the tax amount already rounded per line.
            gross_base = round_amount(tax_data['raw_base_amount_currency'] / (1 - abs(tax.amount) / 100), currency)
            gross_tax = round_amount(gross_base * tax.amount / 100, currency)
            tax_details['raw_total_included_currency'] += gross_tax - tax_data['raw_tax_amount_currency']
            tax_data['raw_base_amount_currency'] = gross_base
            tax_data['raw_tax_amount_currency'] = gross_tax
            tax_data['raw_base_amount'] = to_company_currency(gross_base)
            tax_data['raw_tax_amount'] = to_company_currency(gross_tax)
            tax_details['raw_total_included'] = to_company_currency(tax_details['raw_total_included_currency'])

    @api.model
    def _prepare_base_line_tax_repartition_grouping_key(self, base_line, base_line_grouping_key, tax_data, tax_rep_data):
        # A fully exempt withholding is still declared on the return, keep its zero tax line.
        grouping_key = super()._prepare_base_line_tax_repartition_grouping_key(base_line, base_line_grouping_key, tax_data, tax_rep_data)
        tax = tax_data['tax']
        if tax.country_code == 'GE' and tax.is_withholding_tax:
            grouping_key['__keep_zero_line'] = True
        return grouping_key
