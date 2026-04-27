# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class RentalReport(models.Model):
    _inherit = "sale.rental.report"

    lot_id = fields.Many2one('stock.lot', 'Serial Number', readonly=True)

    def _quantity(self):
        """For the products tracked by serial numbers, we get one unique row for each serial number
        therefore reserved, delivered and returned quantities are required to be set accordingly."""
        return """
            CASE
                WHEN res.stock_lot_id IS NOT NULL
                THEN 1.0
                ELSE product_uom_qty / (u.factor * u2.factor)
                END AS quantity,
            CASE
                WHEN res.stock_lot_id IS NULL
                THEN qty_delivered / (u.factor * u2.factor)
                WHEN returned.stock_lot_id IS NULL AND pickedup.stock_lot_id IS NULL
                THEN 0.0
                ELSE 1.0
                END AS qty_delivered,
            CASE
                WHEN res.stock_lot_id IS NULL
                THEN qty_returned / (u.factor * u2.factor)
                WHEN returned.stock_lot_id IS NOT NULL
                THEN 1.0
                ELSE 0.0
                END AS qty_returned
        """

    def _price(self):
        """For the products tracked by serial numbers, we get one unique row for each serial number
        therefore the price must be set accordingly."""
        price = super()._price()
        return """
            CASE
                WHEN res.stock_lot_id IS NOT NULL AND product_uom_qty != 0
                THEN %s / (product_uom_qty / (u.factor * u2.factor))
                ELSE %s
                END """ % (price, price)

    def _from(self):
        return super(RentalReport, self)._from() + """
            LEFT JOIN rental_reserved_lot_rel AS res ON res.sale_order_line_id=sol.id
            LEFT JOIN rental_pickedup_lot_rel AS pickedup ON pickedup.sale_order_line_id=sol.id
                AND pickedup.stock_lot_id = res.stock_lot_id
            LEFT JOIN rental_returned_lot_rel AS returned ON returned.sale_order_line_id=sol.id
                AND returned.stock_lot_id = res.stock_lot_id
        """

    def _select(self):
        return super(RentalReport, self)._select() + """,
            res.stock_lot_id AS lot_id
        """
