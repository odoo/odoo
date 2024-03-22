from odoo import api, fields, models
from odoo.tools import frozendict



class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_in_reverse_charge = fields.Boolean("Reverse charge", help="Tick this if this tax is reverse charge. Only for Indian accounting")

    def _prepare_dict_for_taxes_computation(self):
        # EXTENDS 'account'
        tax_data = super()._prepare_dict_for_taxes_computation()

        if self.country_code == 'IN':
            l10n_in_tax_type = None
            tags = self.invoice_repartition_line_ids.tag_ids
            if self.env.ref('l10n_in.tax_tag_igst') in tags:
                l10n_in_tax_type = 'igst'
            elif self.env.ref('l10n_in.tax_tag_cgst') in tags:
                l10n_in_tax_type = 'cgst'
            elif self.env.ref('l10n_in.tax_tag_sgst') in tags:
                l10n_in_tax_type = 'sgst'
            elif self.env.ref('l10n_in.tax_tag_cess') in tags:
                l10n_in_tax_type = 'cess'
            tax_data['_l10n_in_tax_type'] = l10n_in_tax_type

        return tax_data

    # -------------------------------------------------------------------------
    # HELPERS IN BOTH PYTHON/JAVASCRIPT (hsn_summary.js / account_tax.py)

    # HSN SUMMARY
    # -------------------------------------------------------------------------

    @api.model
    def _l10n_in_get_hsn_summary_table(self, base_lines, display_uom):
        results_map = {}
        l10n_in_tax_types = set()
        for base_line in base_lines:
            l10n_in_hsn_code = base_line['l10n_in_hsn_code']
            if not l10n_in_hsn_code:
                continue

            price_unit = base_line['price_unit']
            quantity = base_line['quantity']
            product_values = base_line['product_values']
            uom = base_line['uom'] or {}
            taxes_data = base_line['taxes_data']

            # Compute the taxes.
            evaluation_context = self.env['account.tax']._eval_taxes_computation_prepare_context(
                price_unit,
                quantity,
                product_values,
                rounding_method='round_per_line',
                precision_rounding=0.01,
            )
            taxes_computation = self.env['account.tax']._eval_taxes_computation(
                self.env['account.tax']._prepare_taxes_computation(taxes_data),
                evaluation_context,
            )

            # Rate.
            rate = sum(
                tax_data['amount']
                for tax_data in taxes_computation['taxes_data']
                if tax_data['_l10n_in_tax_type'] in ('igst', 'cgst', 'sgst')
            )

            key = frozendict({
                'l10n_in_hsn_code': l10n_in_hsn_code,
                'rate': rate,
                'uom_name': uom.get('name'),
            })

            if key in results_map:
                values = results_map[key]
                values['quantity'] += quantity
                values['amount_untaxed'] += taxes_computation['total_excluded']
            else:
                results_map[key] = {
                    **key,
                    'quantity': quantity,
                    'amount_untaxed': taxes_computation['total_excluded'],
                    'tax_amounts': {
                        'igst': 0.0,
                        'cgst': 0.0,
                        'sgst': 0.0,
                        'cess': 0.0,
                    },
                }

            for tax_data in taxes_computation['taxes_data']:
                l10n_in_tax_type = tax_data['_l10n_in_tax_type']
                if l10n_in_tax_type:
                    results_map[key]['tax_amounts'][l10n_in_tax_type] += tax_data['tax_amount_factorized']
                    l10n_in_tax_types.add(l10n_in_tax_type)

        items = [
            {
                'l10n_in_hsn_code': value['l10n_in_hsn_code'],
                'uom_name': value['uom_name'],
                'rate': value['rate'],
                'quantity': value['quantity'],
                'amount_untaxed': value['amount_untaxed'],
                'tax_amount_igst': value['tax_amounts']['igst'],
                'tax_amount_cgst': value['tax_amounts']['cgst'],
                'tax_amount_sgst': value['tax_amounts']['sgst'],
                'tax_amount_cess': value['tax_amounts']['cess'],
            }
            for value in results_map.values()
        ]
        return {
            'has_igst': 'igst' in l10n_in_tax_types,
            'has_gst': bool({'cgst', 'sgst'} & l10n_in_tax_types),
            'has_cess': 'cess' in l10n_in_tax_types,
            'nb_columns': 5 + len(l10n_in_tax_types),
            'display_uom': display_uom,
            'items': items,
        }
