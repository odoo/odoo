# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import SQL


class PurchaseReport(models.Model):
    _inherit = "purchase.report"

    picking_type_id = fields.Many2one('stock.warehouse', 'Warehouse', readonly=True)
    effective_date = fields.Datetime(string="Effective Date")
    days_to_arrival = fields.Float('Effective Days To Arrival', digits=(16, 2), readonly=True, aggregator='avg')

    def _select(self) -> SQL:
        return SQL(
            """
                %s,
                spt.warehouse_id as picking_type_id, po.effective_date as effective_date,
                extract(
                    epoch from age(
                        COALESCE(
                            po.effective_date,
                            l.date_planned
                        ),
                        po.date_order
                    )
                )/(24*60*60)::decimal(16,2) as days_to_arrival
            """, super()._select()
        )

    def _from(self) -> SQL:
        return SQL(
            """
                %s
                LEFT JOIN stock_picking_type spt ON (spt.id=po.picking_type_id)
            """, super()._from()
        )

    def _group_by(self) -> SQL:
        return SQL("%s, spt.warehouse_id, effective_date", super()._group_by())
