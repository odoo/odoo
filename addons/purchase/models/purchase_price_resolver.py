from typing import NamedTuple

from odoo import api, fields, models


class PriceResolution(NamedTuple):
    seller: fields.Many2one
    price_unit: float
    discount: float
    source: str


class PurchasePriceResolver(models.AbstractModel):
    _name = "purchase.price.resolver"
    _description = "Purchase Price Resolver"

    @api.model
    def _get_seller(
        self, product, *, partner, quantity, uom, date, company, params=None
    ):
        return product.with_company(company)._select_seller(
            partner_id=partner,
            quantity=quantity,
            date=date,
            uom_id=uom,
            params=params,
        )

    @api.model
    def _get_price_resolution(
        self, product, *, seller, uom, currency, company, date, taxes
    ):
        AccountTax = self.env["account.tax"]
        product_taxes = product.supplier_taxes_id
        if seller:
            price_unit = AccountTax._fix_tax_included_price_company(
                seller.price, product_taxes, taxes, company
            )
            price_unit = seller.currency_id._convert(
                price_unit, currency, company, date, round=False
            )
            price_unit = seller.product_uom_id._get_price_estimate(price_unit, uom)
            return PriceResolution(
                seller, price_unit, seller.discount or 0.0, "supplierinfo"
            )
        price_unit = product.uom_id._get_price_estimate(product.standard_price, uom)
        price_unit = AccountTax._fix_tax_included_price_company(
            price_unit, product_taxes, taxes, company
        )
        price_unit = product.cost_currency_id._convert(
            price_unit, currency, company, date, round=False
        )
        return PriceResolution(seller, price_unit, 0.0, "product_cost")
