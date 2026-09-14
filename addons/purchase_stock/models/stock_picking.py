from odoo import _, api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    purchase_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Purchase Order",
        compute="_compute_purchase_id",
        store=True,
        index="btree_not_null",
    )

    def _get_fields_linking_orders(self):
        return ["purchase_id", *super()._get_fields_linking_orders()]

    @api.depends("move_ids.purchase_line_id.order_id")
    def _compute_purchase_id(self):
        for picking in self:
            picking.purchase_id = picking.move_ids.purchase_line_id.order_id

    def _action_done(self):
        _debug.pipeline("purchase_picking_done", pickings=self)
        self.purchase_id.sudo().action_acknowledge()
        return super()._action_done()

    def action_purchase_matching(self):
        return self._get_action_transfer_matching(
            _("Purchase Matching"),
            "purchase.receipt.line.match",
            "purchase_stock.purchase_receipt_line_match_list",
        )
