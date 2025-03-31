# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockLotReport(models.Model):
    _inherit = 'stock.lot.report'

    def _join_on_picking_type_and_partner(self):
        return """
            JOIN stock_picking_type AS type
            ON picking.picking_type_id = type.id and (type.code = 'outgoing' or type.code = 'dropship')
            LEFT JOIN sale_order as so ON so.id = picking.sale_id
            JOIN res_partner AS partner
            ON partner.id = CASE
                WHEN type.code = 'dropship' THEN so.partner_id
                ELSE picking.partner_id
            END
        """
