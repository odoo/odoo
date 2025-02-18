# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _l10n_id_coretax_build_invoice_line_vals(self, vals):
        """ Fill in the vals['lines'] with some information regarding each invoice line"""
        self.ensure_one()
        idr = self.env.ref('base.IDR')

        # initialize
        if not vals.get('lines'):
            vals['lines'] = []

        product = self.product_id

        # Separate tax into the regular and luxury component
        luxury_tax = self.tax_ids.filtered(lambda tax: tax.tax_group_id == self.env.ref(f"account.{self.company_id.id}_l10n_id_tax_group_luxury_goods"))
        regular_tax = self.tax_ids - luxury_tax

        line_val = {
            "Opt": "B" if product.type == "service" else "A",  # A: goods, B: service
            "Code": product.l10n_id_product_code.code or self.env.ref('l10n_id_efaktur_coretax.product_code_000000_goods').code,
            "Name": product.name,
            "Unit": self.product_uom_id.l10n_id_uom_code.code,
            "Price": idr.round(self.price_unit),
            "Qty": self.quantity,
            "TotalDiscount": idr.round(self.discount * self.quantity * self.price_unit / 100),
            "TaxBase": idr.round(self.price_subtotal),  # DPP
            "VATRate": 12,
            "STLGRate": luxury_tax.amount if luxury_tax else 0.0,
        }

        # Code 04 represents "Using other value as tax base". This code is now the norm
        # being used if user is selling non-luxury item where we have to multiply original price
        # by ratio of 11/12 and having VATRate of 12 resulting to effectively 11% tax.
        if self.move_id.l10n_id_kode_transaksi == "04":
            line_val['VATRate'] = 12
            line_val['OtherTaxBase'] = idr.round(self.price_subtotal * 11 / 12)
        # For all other code, OtherTaxBase will follow TaxBase and calculation of VAT should follow the amount of tax itself
        else:
            line_val['VATRate'] = regular_tax.amount
            line_val['OtherTaxBase'] = line_val['TaxBase']

        line_val['VAT'] = idr.round(line_val['OtherTaxBase'] * line_val['VATRate'] / 100)
        line_val['STLG'] = idr.round(line_val['STLGRate'] * line_val['OtherTaxBase'] / 100)

        vals['lines'].append(line_val)
