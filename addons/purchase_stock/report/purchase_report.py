from odoo import fields, models
from odoo.fields import Domain
from odoo.tools import SQL


class PurchaseReport(models.Model):
    _inherit = "purchase.report"

    picking_type_id = fields.Many2one('stock.warehouse', 'Warehouse', readonly=True)
    effective_date = fields.Datetime(string="Effective Date")
    days_to_arrival = fields.Float('Effective Days To Arrival', digits=(16, 2), readonly=True, aggregator='avg')
    qty_total = fields.Float('Total Quantity', readonly=True)
    qty_on_time = fields.Float('On-Time Quantity', readonly=True)
    qty_received = fields.Float('Quantity Received', readonly=True)
    on_time_rate = fields.Float('On-Time Delivery Rate', readonly=True)

    def _select(self) -> SQL:
        return SQL(
            """
                %s,
                spt.warehouse_id as picking_type_id, po.effective_date as effective_date,
                extract(
                    epoch from age(
                        l.date_planned,
                        COALESCE(
                            order_effective_date.date_done,
                            po.date_order
                        )
                    )
                )/(24*60*60)::decimal(16,2) as days_to_arrival,
                SUM(l.product_uom_qty) AS qty_total,
                SUM(COALESCE(delay_data.qty_on_time, 0.0)) AS qty_on_time,
                0.0 AS on_time_rate
            """, super()._select()
        )

    def _from(self) -> SQL:
        return SQL(
            """
                %s
                LEFT JOIN stock_picking_type spt ON (spt.id=po.picking_type_id)
                LEFT JOIN (
                    SELECT MIN(picking.date_done)                                   AS date_done,
                        purchase.id                                                 AS purchase_id
                    FROM purchase_order                                             AS purchase
                    JOIN purchase_order_line                                        AS order_line
                        ON order_line.order_id = purchase.id
                    JOIN stock_move                                                 AS move
                        ON move.purchase_line_id = order_line.id
                    JOIN stock_picking                                              AS picking
                        ON picking.id = move.picking_id
                    JOIN stock_location                                             AS location_dest
                        ON location_dest.id = picking.location_dest_id
                    WHERE picking.state = 'done'
                        AND location_dest.usage != 'supplier'
                        AND picking.date_done IS NOT NULL
                    GROUP BY
                        purchase.id
                ) order_effective_date
                    ON order_effective_date.purchase_id = l.order_id
                LEFT JOIN (
                        SELECT
                            m.purchase_line_id,
                            SUM(m.quantity) AS qty_on_time
                        FROM stock_move m
                        JOIN purchase_order_line pol ON pol.id = m.purchase_line_id
                        WHERE m.state = 'done'
                        GROUP BY m.purchase_line_id
                    ) delay_data ON delay_data.purchase_line_id = l.id
            """, super()._from()
        )

    def _where(self) -> SQL:
        return SQL(
            """
            %s
            AND t.type != 'service'
            AND l.qty_received > 0
            AND l.date_promised IS NOT NULL
            """, super()._where()
        )

    def _group_by(self) -> SQL:
        return SQL("%s, spt.warehouse_id, effective_date, order_effective_date.date_done", super()._group_by())

    def _read_group_select(self, table, aggregate_spec):
        if aggregate_spec == 'on_time_rate:sum':
            # Weighted average
            return SQL(
                'CASE WHEN SUM(%s) !=0 THEN SUM(%s) / SUM(%s) ELSE 1 END',
                table.qty_total, table.qty_on_time, table.qty_total,
            )
        return super()._read_group_select(table, aggregate_spec)

    def _read_group(self, domain, groupby=(), aggregates=(), having=(), offset=0, limit=None, order=None):
        if 'on_time_rate:sum' in aggregates:
            having = Domain.AND([having, [('qty_total:sum', '>', '0')]])
        return super()._read_group(domain, groupby, aggregates, having, offset, limit, order)
