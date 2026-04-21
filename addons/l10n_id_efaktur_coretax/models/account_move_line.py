# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.tools.float_utils import float_repr, float_compare
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _l10n_id_coretax_compute_line_amounts(self):
        """ Compute the raw (unrounded) e-Faktur amounts for this invoice line.
        Used by _l10n_id_coretax_build_invoice_line_vals to build the rounded/formatted line dict. """
        self.ensure_one()

        if float_compare(self.price_subtotal, 0.0, precision_rounding=self.currency_id.rounding) < 0:
            raise ValidationError(_("Price for line '%s' cannot be a negative amount. Please check again.", self.name))

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

        # "price" is unit price calculation excluding tax and discount
        # "total_discount" is total of "price" * quantity * discount
        tax_res = self.tax_ids.compute_all(self.price_unit, quantity=1, currency=self.currency_id, product=self.product_id, partner=self.partner_id, is_refund=self.is_refund)
        price = tax_res['total_excluded']
        tax_base = self.price_subtotal  # DPP

        if ppn_tax:
            if self.move_id.l10n_id_kode_transaksi == "01" or (not regular_tax and not zero_tax):
                other_tax_base = tax_base
            else:
                other_tax_base = self.price_subtotal * 11 / 12
        else:
            other_tax_base = 0

        return {
            'opt': "B" if product.type == "service" else "A",  # A: goods, B: service
            'code': product.l10n_id_product_code.code or self.env.ref('l10n_id_efaktur_coretax.product_code_000000_goods').code,
            'name': product.name,
            'unit': self.product_uom_id.l10n_id_uom_code.code,
            'price': price,
            'qty': self.quantity,
            'total_discount': self.discount * price * self.quantity / 100,
            'tax_base': tax_base,
            'vat_rate': 12 if ppn_tax else 0.0,
            'stlg_rate': stlg_tax.amount if stlg_tax else 0.0,
            'other_tax_base': other_tax_base,
        }

    def _l10n_id_coretax_build_invoice_line_vals(self, vals):
        """ Fill in the vals['lines'] with some information regarding each invoice line"""
        self.ensure_one()
        idr = self.env.ref('base.IDR')

        # initialize
        if not vals.get('lines'):
            vals['lines'] = []

        amounts = self._l10n_id_coretax_compute_line_amounts()

        line_val = {
            "Opt": amounts['opt'],
            "Code": amounts['code'],
            "Name": amounts['name'],
            "Unit": amounts['unit'],
            "Price": idr.round(amounts['price']),
            "Qty": amounts['qty'],
            "TotalDiscount": idr.round(amounts['total_discount']),
            "TaxBase": idr.round(amounts['tax_base']),  # DPP
            "VATRate": amounts['vat_rate'],
            "STLGRate": amounts['stlg_rate'],
            "OtherTaxBase": idr.round(amounts['other_tax_base']),
        }

        line_val['VAT'] = idr.round(line_val['OtherTaxBase'] * line_val['VATRate'] / 100)
        line_val['STLG'] = idr.round(line_val['STLGRate'] * line_val['OtherTaxBase'] / 100)
        # for numerical attributes in line_val, use float_repr to ensure proper formatting
        numerical_fields = ['Price', 'TotalDiscount', 'TaxBase', 'OtherTaxBase', 'VAT', 'STLG']
        for field in numerical_fields:
            line_val[field] = float_repr(line_val[field], precision_digits=self.currency_id.decimal_places)

        vals['lines'].append(line_val)
