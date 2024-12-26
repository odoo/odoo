from odoo import api, fields, models
from odoo.tools import frozendict



class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_in_reverse_charge = fields.Boolean("Reverse charge", help="Tick this if this tax is reverse charge. Only for Indian accounting")
    l10n_in_tax_type = fields.Selection(
        selection=[('igst', 'igst'), ('cgst', 'cgst'), ('sgst', 'sgst'), ('cess', 'cess')],
        compute='_compute_l10n_in_tax_type',
    )

    @api.depends('country_code', 'invoice_repartition_line_ids.tag_ids')
    def _compute_l10n_in_tax_type(self):
        self.l10n_in_tax_type = False
        in_taxes = self.filtered(lambda tax: tax.country_code == 'IN')
        if in_taxes:
            tags_mapping = {
                'igst': self.env.ref('l10n_in.tax_tag_igst'),
                'cgst': self.env.ref('l10n_in.tax_tag_cgst'),
                'sgst': self.env.ref('l10n_in.tax_tag_sgst'),
                'cess': self.env.ref('l10n_in.tax_tag_cess'),
            }
            for tax in in_taxes:
                tags = tax.invoice_repartition_line_ids.tag_ids
                for tag_code, tag in tags_mapping.items():
                    if tag in tags:
                        tax.l10n_in_tax_type = tag_code
                        break

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
            discount = base_line['discount']
            quantity = base_line['quantity']
            product = base_line['product']
            uom = base_line['uom']
            taxes = base_line['taxes_data']

            final_price_unit = price_unit * (1 - (discount / 100))

            # Compute the taxes.
            taxes_computation = taxes._get_tax_details(
                final_price_unit,
                quantity,
                rounding_method='round_per_line',
                product=product,
            )
            # Rate.
            unique_taxes_data = set(
                tax_data['tax']
                for tax_data in taxes_computation['taxes_data']
                if tax_data['tax']['l10n_in_tax_type'] in ('igst', 'cgst', 'sgst')
            )
            rate = sum(tax.amount for tax in unique_taxes_data)

            key = frozendict({
                'l10n_in_hsn_code': l10n_in_hsn_code,
                'rate': rate,
                'uom_name': uom.name,
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
                l10n_in_tax_type = tax_data['tax'].l10n_in_tax_type
                if l10n_in_tax_type:
                    results_map[key]['tax_amounts'][l10n_in_tax_type] += tax_data['tax_amount']
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
