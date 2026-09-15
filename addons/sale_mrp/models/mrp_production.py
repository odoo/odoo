from odoo import _, api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    sale_order_count = fields.Integer(
        string="Count of Source SO",
        compute="_compute_sale_order_count",
        groups="sale.group_sale_salesman",
    )
    sale_line_id = fields.Many2one(
        comodel_name="sale.order.line",
        string="Origin sale order line",
        copy=False,
    )

    @api.depends("reference_ids.sale_ids", "sale_line_id.order_id")
    def _compute_sale_order_count(self):
        for production in self:
            production.sale_order_count = len(production._get_sale_orders())

    def action_view_sale_orders(self):
        self.check_singleton()
        sale_order_ids = self._get_sale_orders().ids
        action = {
            "res_model": "sale.order",
            "type": "ir.actions.act_window",
        }
        if len(sale_order_ids) == 1:
            action.update(
                {
                    "view_mode": "form",
                    "res_id": sale_order_ids[0],
                }
            )
        else:
            action.update(
                {
                    "name": _("Sources Sale Orders of %s", self.name),
                    "domain": [("id", "in", sale_order_ids)],
                    "view_mode": "list,form",
                }
            )
        return action

    def action_confirm(self):
        res = super().action_confirm()
        for production in self.filtered("sale_line_id"):
            _debug.lifecycle(
                "finished_moves_linked_to_sale_line",
                production=production,
                line=production.sale_line_id,
            )
            production.move_finished_ids.filtered(
                lambda move, production=production: (
                    move.product_id == production.product_id
                )
            ).sale_line_id = production.sale_line_id
        return res

    def _get_sale_orders(self):
        return self.reference_ids.sale_ids | self.sale_line_id.order_id

    def _prepare_backorder_mo_vals(self):
        res = super()._prepare_backorder_mo_vals()
        res["sale_line_id"] = self.sale_line_id.id
        return res
