# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools.float_utils import float_repr, float_compare


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _l10n_id_coretax_is_negative_line(self):
        """ Whether this line must be absorbed as a discount by the other lines (e.g. a global discount).

        Intentionally catches any negative line, since Coretax rejects negative <GoodService> amounts.
        """
        self.ensure_one()
        return float_compare(self.price_subtotal, 0.0, precision_rounding=self.currency_id.rounding) < 0

    def _l10n_id_coretax_build_invoice_line_vals(self, vals, base_line):
        """ Fill in the vals['lines'] with some information regarding each invoice line"""
        self.ensure_one()
        idr = self.env.ref('base.IDR')

        # initialize
        if not vals.get('lines'):
            vals['lines'] = []

        product = self.product_id

        # Separate tax into the regular and luxury component
        ChartTemplate = self.env['account.chart.template'].with_company(self.company_id)
        default_tax_group = ChartTemplate.ref('default_tax_group', raise_if_not_found=False)
        non_luxury_tax_group = ChartTemplate.ref('l10n_id_tax_group_non_luxury_goods', raise_if_not_found=False)
        vat_collector_group = ChartTemplate.ref('l10n_id_tax_group_vat_collector', raise_if_not_found=False)
        regular_tax_groups = {default_tax_group, non_luxury_tax_group, vat_collector_group}
        regular_tax_groups.discard(False)
        luxury_tax_group = ChartTemplate.ref('l10n_id_tax_group_luxury_goods', raise_if_not_found=False)
        stlg_tax_group = ChartTemplate.ref('l10n_id_tax_group_stlg', raise_if_not_found=False)
        zero_tax_group_0 = ChartTemplate.ref('l10n_id_tax_group_0', raise_if_not_found=False)
        zero_tax_group_exempt = ChartTemplate.ref('l10n_id_tax_group_exempt', raise_if_not_found=False)
        zero_tax_groups = {zero_tax_group_0, zero_tax_group_exempt}
        zero_tax_groups.discard(False)
        ppn_tax_groups = regular_tax_groups | {luxury_tax_group, stlg_tax_group} | zero_tax_groups
        ppn_tax_groups.discard(False)

        stlg_tax = self.tax_ids.filtered(lambda tax: tax.tax_group_id == stlg_tax_group)
        ppn_tax = self.tax_ids.filtered(lambda tax: tax.tax_group_id in ppn_tax_groups)
        non_luxury_tax = self.tax_ids.filtered(lambda tax: tax.tax_group_id == non_luxury_tax_group)

        tax_details = base_line['tax_details']

        line_val = {
            "Opt": "B" if product.type == "service" else "A",  # A: goods, B: service
            "Code": product.l10n_id_product_code.code or self.env.ref('l10n_id_efaktur_coretax.product_code_000000_goods').code,
            "Name": (self.name or '').replace('\n', ' '),
            "Unit": self.product_uom_id.l10n_id_uom_code.code or self.env.ref('l10n_id_efaktur_coretax.uom_code_0018').code,
            "Price": tax_details['raw_gross_price_unit'],  # excluding tax, before discount
            "Qty": self.quantity,
            "TotalDiscount": tax_details['discount_amount'],  # line discount + absorbed negative lines
            "TaxBase": tax_details['total_excluded'],  # the tax base, after discount
            "VATRate": 12 if ppn_tax else 0.0,
            "STLGRate": stlg_tax.amount if stlg_tax else 0.0,
        }
        if ppn_tax:
            if non_luxury_tax:
                line_val['OtherTaxBase'] = idr.round(line_val['TaxBase'] * 11 / 12)
            else:
                line_val['OtherTaxBase'] = line_val['TaxBase']
        else:
            line_val['OtherTaxBase'] = 0

        # VAT and STLG are computed from the rounded 'OtherTaxBase' on purpose, so that recomputing
        # them from the amounts reported in the XML gives back the very same values.
        line_val['VAT'] = idr.round(line_val['OtherTaxBase'] * line_val['VATRate'] / 100)
        line_val['STLG'] = idr.round(line_val['STLGRate'] * line_val['OtherTaxBase'] / 100)
        # for numerical attributes in line_val, use float_repr to ensure proper formatting
        numerical_fields = ['Price', 'TotalDiscount', 'TaxBase', 'OtherTaxBase', 'VAT', 'STLG']
        for field in numerical_fields:
            line_val[field] = float_repr(line_val[field], precision_digits=self.currency_id.decimal_places)

        vals['lines'].append(line_val)
