# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import SQL


class PurchaseReport(models.Model):
    _inherit = "purchase.report"

    picking_type_id = fields.Many2one('stock.warehouse', 'Warehouse', readonly=True)
    effective_date = fields.Datetime(string="Effective Date")
    days_to_arrival = fields.Float('Effective Days To Arrival', digits=(16, 2), readonly=True, aggregator='avg')

    def _select_list(self, table):
        table._query.add_join('LEFT JOIN', 'order_effective_date', SQL("""(
            SELECT MIN(picking.date_done) AS date_done,
                   purchase.id AS purchase_id
              FROM purchase_order AS purchase
              JOIN purchase_order_line AS order_line
                ON order_line.order_id = purchase.id
              JOIN stock_move AS move
                ON move.purchase_line_id = order_line.id
              JOIN stock_picking AS picking
                ON picking.id = move.picking_id
              JOIN stock_location AS location_dest
                ON location_dest.id = picking.location_dest_id
             WHERE picking.state = 'done'
               AND location_dest.usage != 'supplier'
               AND picking.date_done IS NOT NULL
          GROUP BY purchase.id
        )"""), SQL("order_effective_date.purchase_id = %s", table.order_id))
        return super()._select_list(table) + [
            SQL("%s AS picking_type_id", table.order_id.picking_type_id.warehouse_id),
            table.order_id.effective_date,
            SQL(
                """EXTRACT(epoch FROM AGE(%s, COALESCE(order_effective_date.date_done, %s)))/(24*60*60)::decimal(16,2) as days_to_arrival""",
                table.date_planned, table.order_id.date_order,
            ),
        ]

    def _groupby_list(self, table):
        return super()._groupby_list(table) + [
            table.order_id.picking_type_id.warehouse_id,
            SQL("order_effective_date.date_done"),
        ]
