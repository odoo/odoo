# © 2018 Iván Todorovich <ivan.todorovich@gmail.com>
# © 2019-Today GRAP
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class TileCategory(models.Model):
    _name = "tile.category"
    _description = "Dashboard Tile Category"
    _order = "sequence asc"

    name = fields.Char(required=True)
    sequence = fields.Integer(required=True, default=10)
    active = fields.Boolean(default=True)
    action_id = fields.Many2one(
        string="Odoo Action",
        comodel_name="ir.actions.act_window",
        readonly=True,
    )
    menu_id = fields.Many2one(
        string="Odoo Menu",
        comodel_name="ir.ui.menu",
        readonly=True,
    )
    tile_ids = fields.One2many(
        string="Tiles",
        comodel_name="tile.tile",
        inverse_name="category_id",
    )
    tile_qty = fields.Integer(
        string="Tiles Quantity",
        compute="_compute_tile_qty",
        store=True,
    )

    @api.depends("tile_ids")
    def _compute_tile_qty(self):
        for category in self:
            category.tile_qty = len(category.tile_ids)

    # --- UI auto-management ---

    def _prepare_action(self):
        self.ensure_one()
        view_ref = self.env.ref(
            "web_dashboard_tile.view_tile_tile_kanban",
            raise_if_not_found=False,
        )
        return {
            "name": self.name,
            "res_model": "tile.tile",
            "type": "ir.actions.act_window",
            "view_mode": "kanban,list,form",
            "view_id": view_ref.id if view_ref else False,
            "domain": (
                "['|', ('user_id', '=', False), ('user_id', '=', uid),"
                " ('category_id', '=', %d)]" % self.id
            ),
        }

    def _prepare_menu(self):
        self.ensure_one()
        parent = self.env.ref("web_dashboard_tile.menu_dashboard_tile")
        return {
            "name": self.name,
            "parent_id": parent.id,
            "action": "ir.actions.act_window,%d" % self.action_id.id,
            "sequence": self.sequence,
        }

    def _create_ui(self):
        ActWindow = self.env["ir.actions.act_window"]
        Menu = self.env["ir.ui.menu"]
        for category in self:
            try:
                category._create_action(ActWindow)
                category._create_menu(Menu)
            except Exception:
                _logger.warning(
                    "Failed to create UI for category '%s' (id=%s)",
                    category.name,
                    category.id,
                    exc_info=True,
                )

    def _create_action(self, ActWindow):
        """Create or update the window action for this category."""
        self.ensure_one()
        action_vals = self._prepare_action()
        if not self.action_id:
            self.action_id = ActWindow.create(action_vals)
        else:
            self.action_id.write(action_vals)

    def _create_menu(self, Menu):
        """Create the menu entry for this category if missing."""
        self.ensure_one()
        if not self.menu_id:
            self.menu_id = Menu.create(self._prepare_menu())

    def _delete_ui(self):
        for category in self:
            try:
                if category.menu_id:
                    category.menu_id.unlink()
                if category.action_id:
                    category.action_id.unlink()
            except Exception:
                _logger.warning(
                    "Failed to delete UI for category '%s' (id=%s)",
                    category.name,
                    category.id,
                    exc_info=True,
                )

    # --- CRUD overrides ---

    @api.model_create_multi
    def create(self, vals_list):
        categories = super().create(vals_list)
        categories.filtered("active")._create_ui()
        return categories

    def write(self, vals):
        res = super().write(vals)
        if "active" in vals:
            if vals["active"]:
                self._create_ui()
            else:
                self._delete_ui()
        if "sequence" in vals:
            self.mapped("menu_id").write({"sequence": vals["sequence"]})
        if "name" in vals:
            self.mapped("menu_id").write({"name": vals["name"]})
            self.mapped("action_id").write({"name": vals["name"]})
        return res

    def unlink(self):
        self._delete_ui()
        return super().unlink()
