from odoo import models
from odoo.tools import SQL


class SaleReport(models.Model):
    _inherit = "sale.report"

    def _select_pos_dict(self, table):
        order_rate = self._case_value_or_one(table.order_id.currency_rate)
        return super()._select_pos_dict(table) | {
            'untaxed_delivered_amount': SQL(
                "(CASE WHEN %s IS NOT NULL THEN SUM(%s * %s) ELSE 0 END) / MIN(%s) * %s",
                table.order_id.account_move, table.price_unit, table.qty_delivered, order_rate, table.consolidation_rate,
            ),
            'warehouse_id': table.order_id.session_id.config_id.picking_type_id.warehouse_id,
        }

    def _groupby_pos_list(self, table):
        return super()._groupby_pos_list(table) + [table.order_id.session_id.config_id.picking_type_id.id]
