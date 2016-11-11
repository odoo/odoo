# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.sql import drop_view_if_exists


class ReportStockLinesDate(models.Model):
    _name = "report.stock.lines.date"
    _description = "Dates of Inventories and latest Moves"
    _auto = False
    _order = "date"

    id = fields.Integer('Product Id', readonly=True)
    product_id = fields.Many2one('product.product', 'Product', readonly=True, index=True)
    date = fields.Datetime('Date of latest Inventory', readonly=True)
    move_date = fields.Datetime('Date of latest Stock Move', readonly=True)
    active = fields.Boolean("Active", readonly=True)

    @api.model_cr
    def init(self):
        drop_view_if_exists(self._cr, 'report_stock_lines_date')
        self._cr.execute("""
            create or replace view report_stock_lines_date as (
                select
                p.id as id,
                p.id as product_id,
                max(s.date) as date,
                max(m.date) as move_date,
                p.active as active
            from
                product_product p
                    left join (
                        stock_inventory_line l
                        inner join stock_inventory s on (l.inventory_id=s.id and s.state = 'done')
                    ) on (p.id=l.product_id)
                    left join stock_move m on (m.product_id=p.id and m.state = 'done')
                group by p.id
            )""")
