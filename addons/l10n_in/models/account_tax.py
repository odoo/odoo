from collections import defaultdict

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

    def _prepare_base_line_for_taxes_computation(self, record, **kwargs):
        # EXTENDS 'account'
        results = super()._prepare_base_line_for_taxes_computation(record, **kwargs)
        results['l10n_in_hsn_code'] = self._get_base_line_field_value_from_record(record, 'l10n_in_hsn_code', kwargs, False)
        return results

    @api.model
    def _l10n_in_get_hsn_summary_table(self, base_lines, display_uom):
        l10n_in_tax_types = set()
        items_map = defaultdict(lambda: {
            'quantity': 0.0,
            'amount_untaxed': 0.0,
            'tax_amount_igst': 0.0,
            'tax_amount_cgst': 0.0,
            'tax_amount_sgst': 0.0,
            'tax_amount_cess': 0.0,
        })

        def get_base_line_grouping_key(base_line):
            unique_taxes_data = set(
                tax_data['tax']
                for tax_data in base_line['tax_details']['taxes_data']
                if tax_data['tax']['l10n_in_tax_type'] in ('igst', 'cgst', 'sgst')
            )
            rate = sum(tax.amount for tax in unique_taxes_data)

            return {
                'l10n_in_hsn_code': base_line['l10n_in_hsn_code'],
                'uom_name': base_line['product_uom_id'].name,
                'rate': rate,
            }

        # quantity / amount_untaxed.
        for base_line in base_lines:
            key = frozendict(get_base_line_grouping_key(base_line))
            if not key['l10n_in_hsn_code']:
                continue

            item = items_map[key]
            item['quantity'] += base_line['quantity']
            item['amount_untaxed'] += (
                base_line['tax_details']['total_excluded_currency']
                + base_line['tax_details']['delta_total_excluded_currency']
            )

        # Tax amounts.
        def grouping_function(base_line, tax_data):
            return {
                **get_base_line_grouping_key(base_line),
                'l10n_in_tax_type': tax_data['tax'].l10n_in_tax_type,
            }

        base_lines_aggregated_values = self._aggregate_base_lines_tax_details(base_lines, grouping_function)
        values_per_grouping_key = self._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        for grouping_key, values in values_per_grouping_key.items():
            if (
                not grouping_key
                or not grouping_key['l10n_in_hsn_code']
                or not grouping_key['l10n_in_tax_type']
            ):
                continue

            key = frozendict({
                'l10n_in_hsn_code': grouping_key['l10n_in_hsn_code'],
                'rate': grouping_key['rate'],
                'uom_name': grouping_key['uom_name'],
            })
            item = items_map[key]
            l10n_in_tax_type = grouping_key['l10n_in_tax_type']
            item[f'tax_amount_{l10n_in_tax_type}'] += values['tax_amount_currency']
            l10n_in_tax_types.add(l10n_in_tax_type)

        return {
            'has_igst': 'igst' in l10n_in_tax_types,
            'has_gst': bool({'cgst', 'sgst'} & l10n_in_tax_types),
            'has_cess': 'cess' in l10n_in_tax_types,
            'nb_columns': 5 + len(l10n_in_tax_types),
            'display_uom': display_uom,
            'items': [
                key | values
                for key, values in items_map.items()
            ],
        }
