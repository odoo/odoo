# -*- coding: utf-8 -*-
"""
@author: Online ERP Hungary Kft.
"""

from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _set_price_and_tax_after_fpos(self):
        result = super(AccountMoveLine, self)._set_price_and_tax_after_fpos()

        if self.tax_ids and self.move_id.fiscal_position_id:
            # Need to provide the product to map_tax
            self.tax_ids = self.move_id.fiscal_position_id.map_tax(self.tax_ids._origin, product=self.product_id)

        return result

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for line in self:
            if not line.product_id or line.display_type in ("line_section", "line_note"):
                continue

            line.name = line._get_computed_name()
            line.account_id = line._get_computed_account()
            taxes = line._get_computed_taxes()
            if taxes and line.move_id.fiscal_position_id:
                ############ FROM HERE ############
                # Need to provide the product to map_tax
                taxes = line.move_id.fiscal_position_id.map_tax(taxes, line.product_id)
                ############ TO HERE ############
            line.tax_ids = taxes
            line.product_uom_id = line._get_computed_uom()
            line.price_unit = line._get_computed_price_unit()

    def _get_computed_price_unit(self):
        """Helper to get the default price unit based on the product by taking care of the taxes
        set on the product and the fiscal position.
        :return: The price unit.
        """
        self.ensure_one()

        if not self.product_id:
            return 0.0

        company = self.move_id.company_id
        currency = self.move_id.currency_id
        company_currency = company.currency_id
        product_uom = self.product_id.uom_id
        fiscal_position = self.move_id.fiscal_position_id
        is_refund_document = self.move_id.move_type in ("out_refund", "in_refund")
        move_date = self.move_id.date or fields.Date.context_today(self)

        if self.move_id.is_sale_document(include_receipts=True):
            product_price_unit = self.product_id.lst_price
            product_taxes = self.product_id.taxes_id
        elif self.move_id.is_purchase_document(include_receipts=True):
            product_price_unit = self.product_id.standard_price
            product_taxes = self.product_id.supplier_taxes_id
        else:
            return 0.0
        product_taxes = product_taxes.filtered(lambda tax: tax.company_id == company)

        # Apply unit of measure.
        if self.product_uom_id and self.product_uom_id != product_uom:
            product_price_unit = product_uom._compute_price(product_price_unit, self.product_uom_id)

        # Apply fiscal position.
        if product_taxes and fiscal_position:
            ############ FROM HERE ############
            # Need to provide the product to map_tax
            product_taxes_after_fp = fiscal_position.map_tax(product_taxes, self.product_id)
            ############ TO HERE ############

            if set(product_taxes.ids) != set(product_taxes_after_fp.ids):
                flattened_taxes_before_fp = product_taxes._origin.flatten_taxes_hierarchy()
                if any(tax.price_include for tax in flattened_taxes_before_fp):
                    taxes_res = flattened_taxes_before_fp.compute_all(
                        product_price_unit,
                        quantity=1.0,
                        currency=company_currency,
                        product=self.product_id,
                        partner=self.partner_id,
                        is_refund=is_refund_document,
                    )
                    product_price_unit = company_currency.round(taxes_res["total_excluded"])

                flattened_taxes_after_fp = product_taxes_after_fp._origin.flatten_taxes_hierarchy()
                if any(tax.price_include for tax in flattened_taxes_after_fp):
                    taxes_res = flattened_taxes_after_fp.compute_all(
                        product_price_unit,
                        quantity=1.0,
                        currency=company_currency,
                        product=self.product_id,
                        partner=self.partner_id,
                        is_refund=is_refund_document,
                        handle_price_include=False,
                    )
                    for tax_res in taxes_res["taxes"]:
                        tax = self.env["account.tax"].browse(tax_res["id"])
                        if tax.price_include:
                            product_price_unit += tax_res["amount"]

        # Apply currency rate.
        if currency and currency != company_currency:
            product_price_unit = company_currency._convert(product_price_unit, currency, company, move_date)

        return product_price_unit

    @api.onchange("product_uom_id")
    def _onchange_uom_id(self):
        """Recompute the 'price_unit' depending of the unit of measure."""
        if self.display_type in ("line_section", "line_note"):
            return
        taxes = self._get_computed_taxes()
        if taxes and self.move_id.fiscal_position_id:
            ############ FROM HERE ############
            # Need to provide the product to map_tax
            taxes = self.move_id.fiscal_position_id.map_tax(taxes, self.product_id)
            ############ TO HERE ############
        self.tax_ids = taxes
        self.price_unit = self._get_computed_price_unit()
