from odoo import Command, api, fields, models

from ..tools import debug_log as dbg
from odoo.addons.stock.const import OUTGOING_BLOCK_TYPES


class PosConfigStock(models.Model):
    _inherit = "pos.config"

    show_stock_in_pos = fields.Boolean(
        string="Show Stock Quantities",
        default=True,
        help="Display product stock quantities on POS product cards",
    )
    stock_display_location = fields.Selection(
        selection=[
            ("top_left", "Top Left"),
            ("top_right", "Top Right"),
            ("bottom_left", "Bottom Left"),
            ("bottom_right", "Bottom Right"),
        ],
        string="Stock Display Position",
        default="top_left",
        required=True,
        help="Position where stock quantity will be displayed on product cards",
    )
    low_stock_threshold = fields.Float(
        default=10.0,
        help="Products with stock below this threshold will be highlighted as low stock",
    )
    stock_warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        check_company=True,
        help="Select specific warehouse for stock display. Leave empty to show total from all warehouses.",
    )
    stock_warehouse_view_location_id = fields.Many2one(
        related="stock_warehouse_id.view_location_id",
        string="Warehouse View Location",
    )
    stock_location_ids = fields.Many2many(
        comodel_name="stock.location",
        relation="pos_config_stock_location_rel",
        column1="config_id",
        column2="location_id",
        string="Stock Locations",
        domain="[('usage', '=', 'internal')]",
        help="Select specific locations to count stock from. Leave empty to use all locations from the warehouse.",
    )

    @api.onchange("stock_warehouse_id")
    def _onchange_stock_warehouse_id(self):
        self.stock_location_ids = [Command.clear()]

    def _get_stock_scope(self):
        if self.stock_location_ids:
            return "location", self.stock_location_ids.ids
        if self.stock_warehouse_id:
            return "warehouse_id", self.stock_warehouse_id.ids
        return None

    def _prepare_stock_quantity_context(self):
        scope = self._get_stock_scope()
        return dict([scope]) if scope else {}

    def _get_stock_locations(self):
        Location = self.env["stock.location"]
        scope = self._get_stock_scope()
        if scope and scope[0] == "location":
            roots = scope[1]
        else:
            warehouses = (
                self.stock_warehouse_id
                if scope
                else self.env["stock.warehouse"].search(
                    [("company_id", "in", self.env.companies.ids)]
                )
            )
            roots = warehouses.view_location_id.ids
        if not roots:
            dbg.logic.debug("[config:%s] no stock roots: no locations", self.id)
            return Location
        domain = [("location_id", "child_of", roots), ("usage", "=", "internal")]
        if not self.env.user.has_group("stock.group_stock_user"):
            domain.append(("effective_block_type", "not in", OUTGOING_BLOCK_TYPES))
        locations = Location.search(domain)
        dbg.logic.debug(
            "[config:%s] stock scope %s roots=%s -> %s",
            self.id,
            scope,
            roots,
            dbg.rec(locations),
        )
        return locations
