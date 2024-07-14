# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class RentalSchedule(models.Model):
    _inherit = "sale.rental.schedule"

    is_available = fields.Boolean(compute='_compute_is_available', readonly=True, compute_sudo=True)

    lot_id = fields.Many2one('stock.lot', 'Serial Number', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', readonly=True)
    # TODO color depending on report_line_status

    def _compute_is_available(self):
        quoted_rentals_with_product = self.filtered(
            lambda r: r.rental_status not in ['return', 'returned', 'cancel']
                and r.return_date > fields.Datetime.now()
                and r.product_id.type == 'product')
        for rental in quoted_rentals_with_product:
            sol = rental.order_line_id
            rental.is_available = sol.virtual_available_at_date - sol.product_uom_qty >= 0
        (self - quoted_rentals_with_product).is_available = True

    def _get_product_name(self):
        lang = self.env.lang or 'en_US'
        return f"""COALESCE(lot_info.name, NULLIF(t.name->>'{lang}', ''), t.name->>'en_US') as product_name"""

    def _id(self):
        return """ROW_NUMBER() OVER () AS id"""

    def _quantity(self):
        return """
            CASE WHEN lot_info.lot_id IS NULL then sum(sol.product_uom_qty / u.factor * u2.factor) ELSE 1.0 END as product_uom_qty,
            CASE WHEN lot_info.lot_id IS NULL then sum(sol.qty_delivered / u.factor * u2.factor)
                WHEN lot_info.report_line_status = 'reserved' then 0.0
                ELSE 1.0 END as qty_delivered,
            CASE WHEN lot_info.lot_id IS NULL then sum(sol.qty_returned / u.factor * u2.factor)
                WHEN lot_info.report_line_status = 'returned' then 1.0
                ELSE 0.0 END as qty_returned
        """

    def _late(self):
        return """
            CASE when lot_info.lot_id is NULL then
                CASE WHEN s.rental_start_date < NOW() AT TIME ZONE 'UTC' AND sol.qty_delivered < sol.product_uom_qty THEN TRUE
                    WHEN s.rental_return_date < NOW() AT TIME ZONE 'UTC' AND sol.qty_returned < sol.qty_delivered THEN TRUE
                    ELSE FALSE
                END
            ELSE
                CASE WHEN lot_info.report_line_status = 'returned' THEN FALSE
                    WHEN lot_info.report_line_status = 'pickedup' THEN
                        CASE WHEN s.rental_return_date < NOW() AT TIME ZONE 'UTC' THEN TRUE
                        ELSE FALSE
                        END
                    ELSE
                        CASE WHEN s.rental_start_date < NOW() AT TIME ZONE 'UTC' THEN TRUE
                        ELSE FALSe
                        END
                END
            END as late
        """

    def _report_line_status(self):
        return """
            CASE when lot_info.lot_id is NULL then
                CASE when sol.qty_returned = sol.qty_delivered AND sol.qty_delivered = sol.product_uom_qty then 'returned'
                    when sol.qty_delivered = sol.product_uom_qty then 'pickedup'
                    else 'reserved'
                END
            ELSE lot_info.report_line_status
            END as report_line_status
        """

    def _color(self):
        """2 = orange, 4 = blue, 6 = red, 7 = green"""
        return """
            CASE when lot_info.lot_id is NULL then
                CASE WHEN s.rental_start_date < NOW() AT TIME ZONE 'UTC' AND sol.qty_delivered < sol.product_uom_qty THEN 4
                    WHEN s.rental_return_date < NOW() AT TIME ZONE 'UTC' AND sol.qty_returned < sol.qty_delivered THEN 6
                    when sol.qty_returned = sol.qty_delivered AND sol.qty_delivered = sol.product_uom_qty THEN 7
                    WHEN sol.qty_delivered = sol.product_uom_qty THEN 2
                    ELSE 4
                END
            ELSE
                CASE WHEN lot_info.report_line_status = 'returned' THEN 7
                    WHEN lot_info.report_line_status = 'pickedup' THEN
                        CASE WHEN s.rental_return_date < NOW() AT TIME ZONE 'UTC' THEN 6
                        ELSE 2
                        END
                    ELSE 4
                END
            END as color
        """

    def _with(self):
        return """
            WITH ordered_lots (lot_id, name, sol_id, report_line_status) AS
                (SELECT
                    lot.id as lot_id,
                    lot.name,
                    COALESCE(res.sale_order_line_id, pickedup.sale_order_line_id) as sol_id,
                    CASE
                        WHEN returned.stock_lot_id IS NOT NULL THEN 'returned'
                        WHEN pickedup.stock_lot_id IS NOT NULL THEN 'pickedup'
                        ELSE 'reserved'
                    END AS report_line_status
                    FROM
                        rental_reserved_lot_rel res
                    FULL OUTER JOIN rental_pickedup_lot_rel pickedup
                        ON res.sale_order_line_id=pickedup.sale_order_line_id
                        AND res.stock_lot_id=pickedup.stock_lot_id
                    LEFT OUTER JOIN rental_returned_lot_rel returned
                        ON returned.sale_order_line_id=pickedup.sale_order_line_id
                        AND returned.stock_lot_id=pickedup.stock_lot_id
                    JOIN stock_lot lot
                        ON res.stock_lot_id=lot.id
                        OR pickedup.stock_lot_id=lot.id
                UNION ALL
                SELECT DISTINCT ON (sml.lot_id)
                    sml.lot_id,
                    sl.name,
                    sol.id AS sol_id,
                    CASE
                        WHEN so.rental_status='returned' THEN 'returned'
                        WHEN so.rental_status='return' THEN 'pickedup'
                        WHEN so.rental_status='pickup' THEN 'reserved'
                    END AS report_line_status
                FROM sale_order so
                    INNER JOIN sale_order_line sol ON so.id=sol.order_id
                    INNER JOIN stock_lot sl ON sol.product_id=sl.product_id
                    INNER JOIN stock_move_line sml ON sl.id=sml.lot_id
                    INNER JOIN stock_picking sp ON sol.order_id=sp.sale_id
                    INNER JOIN stock_move sm ON sml.move_id=sm.id
                WHERE sm.sale_line_id=sol.id
                    AND so.is_rental_order=true
                )
        """

    def _select(self):
        return super(RentalSchedule, self)._select() + """,
            lot_info.lot_id as lot_id,
            s.warehouse_id as warehouse_id
        """

    def _from(self):
        return super(RentalSchedule, self)._from() + """
            LEFT OUTER JOIN ordered_lots lot_info ON sol.id=lot_info.sol_id
        """

    def _groupby(self):
        # Add ORDER BY to ensure that `ROW_NUMBER() OVER () AS id` targets the same row each time
        return super(RentalSchedule, self)._groupby() + """,
            lot_info.lot_id,
            lot_info.name,
            lot_info.report_line_status
        ORDER BY sol.id, lot_info.lot_id"""
