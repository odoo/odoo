# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.tools import format_amount


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # -----------------------
    # CRUD, inherited methods
    # -----------------------

    def _construct_tax_string(self, price):
        """ Updates the tax string computation to include the withheld amount when withholding taxes are involved. """
        # OVERRIDE 'account'
        company_taxes = self.taxes_id.filtered(lambda t: t.company_id == self.env.company)

        def _get_withheld_amount():
            if not company_taxes:
                return 0.0

            base_line = company_taxes._prepare_base_line_for_taxes_computation(
                None,
                partner_id=self.env["res.partner"],
                currency_id=self.env.company.currency_id,
                product_id=self,
                quantity=1.0,
                tax_ids=company_taxes,
                price_unit=price,
                calculate_withholding_taxes=True,
            )
            company_taxes._add_tax_details_in_base_line(base_line, self.env.company)
            company_taxes._round_base_lines_tax_details([base_line], self.env.company)
            company_taxes._add_accounting_data_to_base_line_tax_details(
                base_line,
                self.env.company,
            )
            tax_details = base_line['tax_details']
            wth_total = 0.0
            for tax_data in tax_details['taxes_data']:
                if tax_data['tax'].is_withholding_tax_on_payment:
                    wth_total -= tax_data['tax_amount_currency']
            return wth_total

        # Reimplement the tax string by taking into account the withholding taxes.
        # First step; compute the amounts excluding withholding taxes.
        res = company_taxes.compute_all(
            price, product=self, partner=self.env['res.partner']
        )
        joined = []
        included = res['total_included']
        excluded = res['total_excluded']
        # Second step, compute the withholding tax amounts
        withheld_amount = _get_withheld_amount()

        currency = self.currency_id
        if currency.compare_amounts(included, price):
            joined.append(self.env._('%(amount)s Incl. Taxes', amount=format_amount(self.env, included, currency)))
        if currency.compare_amounts(excluded, price):
            joined.append(self.env._('%(amount)s Excl. Taxes', amount=format_amount(self.env, excluded, currency)))
        if not currency.is_zero(withheld_amount):
            joined.append(self.env._('%(amount)s Tax Withheld', amount=format_amount(self.env, withheld_amount, currency)))
        if joined:
            tax_string = f"(= {', '.join(joined)})"
        else:
            tax_string = " "
        return tax_string
