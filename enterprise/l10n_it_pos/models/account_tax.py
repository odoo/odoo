from odoo import api, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    @api.model
    def _prepare_base_line_for_taxes_computation(self, record, **kwargs):
        # EXTENDS 'account'
        base_line = super()._prepare_base_line_for_taxes_computation(record, **kwargs)
        base_line['l10n_it_epson_printer'] = kwargs.get('l10n_it_epson_printer', False)
        return base_line

    @api.model
    def _add_tax_details_in_base_line(self, base_line, company, rounding_method=None):
        # EXTENDS 'account'
        if (
            base_line['l10n_it_epson_printer']
            and not base_line['special_mode']
            and len(base_line['tax_ids']) == 1
            and base_line['tax_ids'][0].amount_type == 'percent'
            and not base_line['tax_ids'][0].price_include
        ):
            new_base_line = self._prepare_base_line_for_taxes_computation(base_line, quantity=1, discount=0)
            super()._add_tax_details_in_base_line(new_base_line, company, rounding_method=rounding_method)
            super()._round_base_lines_tax_details([new_base_line], company)
            tax_details = new_base_line['tax_details']
            price_unit_included = tax_details['total_included_currency']
            new_base_line = self._prepare_base_line_for_taxes_computation(
                base_line,
                price_unit=price_unit_included,
                special_mode='total_included',
            )
            super()._add_tax_details_in_base_line(new_base_line, company, rounding_method=rounding_method)
            super()._round_base_lines_tax_details([new_base_line], company)
            tax_details = new_base_line['tax_details']
            base_line['manual_tax_amounts'] = {
                str(tax_data['tax'].id): {
                    'tax_amount_currency': tax_data['tax_amount_currency'],
                    'base_amount_currency': tax_data['base_amount_currency'],
                }
                for tax_data in tax_details['taxes_data']
            }
        super()._add_tax_details_in_base_line(base_line, company, rounding_method=rounding_method)
