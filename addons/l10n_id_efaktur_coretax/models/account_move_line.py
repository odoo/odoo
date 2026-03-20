# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.tools.float_utils import float_repr, float_compare
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _l10n_id_coretax_build_invoice_line_vals(self, vals):
        """ Fill in the vals['lines'] with some information regarding each invoice line"""
        self.ensure_one()
        idr = self.env.ref('base.IDR')

        if float_compare(self.price_subtotal, 0.0, precision_rounding=self.currency_id.rounding) < 0:
            raise ValidationError(_("Price for line '%s' cannot be a negative amount. Please check again.", self.name))

        # initialize
        if not vals.get('lines'):
            vals['lines'] = []

        product = self.product_id

        # Separate tax into the regular and luxury component
        ChartTemplate = self.env['account.chart.template'].with_company(self.company_id)
        default_tax_group = ChartTemplate.ref('default_tax_group', raise_if_not_found=False)
        non_luxury_tax_group = ChartTemplate.ref('l10n_id_tax_group_non_luxury_goods', raise_if_not_found=False)
        regular_tax_groups = {default_tax_group, non_luxury_tax_group}
        regular_tax_groups.discard(False)
        luxury_tax_group = ChartTemplate.ref('l10n_id_tax_group_luxury_goods', raise_if_not_found=False)
        stlg_tax_group = ChartTemplate.ref('l10n_id_tax_group_stlg', raise_if_not_found=False)
        zero_tax_group_0 = ChartTemplate.ref('l10n_id_tax_group_0', raise_if_not_found=False)
        zero_tax_group_exempt = ChartTemplate.ref('l10n_id_tax_group_exempt', raise_if_not_found=False)
        zero_tax_groups = {zero_tax_group_0, zero_tax_group_exempt}
        zero_tax_groups.discard(False)
        ppn_tax_groups = regular_tax_groups | {luxury_tax_group, stlg_tax_group} | zero_tax_groups
        ppn_tax_groups.discard(False)

        zero_tax = self.tax_ids.filtered(lambda tax: tax.tax_group_id in zero_tax_groups)
        stlg_tax = self.tax_ids.filtered(lambda tax: tax.tax_group_id == stlg_tax_group)
        regular_tax = self.tax_ids.filtered(lambda tax: tax.tax_group_id in regular_tax_groups)
        ppn_tax = self.tax_ids.filtered(lambda tax: tax.tax_group_id in ppn_tax_groups)

        # "Price" is unit price calculation excluding tax and discount
        # "TotalDiscount" is total of "Price" * quantity * discount
        tax_res = self.tax_ids.compute_all(self.price_unit, quantity=1, currency=self.currency_id, product=self.product_id, partner=self.partner_id, is_refund=self.is_refund)

        line_val = {
            "Opt": "B" if product.type == "service" else "A",  # A: goods, B: service
            "Code": product.l10n_id_product_code.code or self.env.ref('l10n_id_efaktur_coretax.product_code_000000_goods').code,
            "Name": product.name,
            "Unit": self.product_uom_id.l10n_id_uom_code.code,
            "Price": idr.round(tax_res['total_excluded']),
            "Qty": self.quantity,
            "TotalDiscount": idr.round(self.discount * tax_res['total_excluded'] * self.quantity / 100),
            "TaxBase": idr.round(self.price_subtotal),  # DPP
            "VATRate": 12 if ppn_tax else 0.0,
            "STLGRate": stlg_tax.amount if stlg_tax else 0.0,
        }
        if ppn_tax:
            if self.move_id.l10n_id_kode_transaksi == "01" or (not regular_tax and not zero_tax):
                line_val['OtherTaxBase'] = line_val['TaxBase']
            else:
                line_val['OtherTaxBase'] = idr.round(self.price_subtotal * 11 / 12)
        else:
            line_val['OtherTaxBase'] = 0

        line_val['VAT'] = idr.round(line_val['OtherTaxBase'] * line_val['VATRate'] / 100)
        line_val['STLG'] = idr.round(line_val['STLGRate'] * line_val['OtherTaxBase'] / 100)
        # for numerical attributes in line_val, use float_repr to ensure proper formatting
        numerical_fields = ['Price', 'TotalDiscount', 'TaxBase', 'OtherTaxBase', 'VAT', 'STLG']
        for field in numerical_fields:
            line_val[field] = float_repr(line_val[field], precision_digits=self.currency_id.decimal_places)

        vals['lines'].append(line_val)
