from odoo import api, fields, models
from odoo.tools.translate import _


class StockPicking(models.Model):
    _inherit = "stock.picking"

    # ------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------

    purchase_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Purchase Order",
        compute="_compute_purchase_id",
        store=True,
        index="btree_not_null",
    )
    delay_pass = fields.Datetime(
        compute="_compute_date_order",
        search="_search_delay_pass",
        copy=False,
        index=True,
    )
    days_to_arrive = fields.Datetime(
        compute="_compute_date_effective",
        search="_search_days_to_arrive",
        copy=False,
    )

    # ------------------------------------------------------------
    # COMPUTE METHODS
    # ------------------------------------------------------------

    def _compute_date_order(self):
        for picking in self:
            picking.delay_pass = (
                picking.purchase_id.date_order
                if picking.purchase_id
                else fields.Datetime.now()
            )

    @api.depends("move_ids.purchase_line_id.order_id")
    def _compute_purchase_id(self):
        for picking in self:
            # picking and move should have a link to the SO to see the picking on the stat button.
            picking.purchase_id = picking.move_ids.purchase_line_id.order_id

    @api.depends("state", "location_dest_id.usage", "date_done")
    def _compute_date_effective(self):
        for picking in self:
            if (
                picking.state == "done"
                and picking.location_dest_id.usage != "supplier"
                and picking.date_done
            ):
                picking.days_to_arrive = picking.date_done
            else:
                picking.days_to_arrive = False

    # ------------------------------------------------------------
    # SEARCH METHODS
    # ------------------------------------------------------------

    @api.model
    def _search_days_to_arrive(self, operator, value):
        return [("date_done", operator, value)]

    @api.model
    def _search_delay_pass(self, operator, value):
        return [("purchase_id.date_order", operator, value)]

    # ------------------------------------------------------------
    # ACTION METHODS
    # ------------------------------------------------------------

    def _action_done(self):
        self.purchase_id.sudo().action_acknowledge()
        return super()._action_done()
