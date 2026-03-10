# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.


from odoo.http import request
from odoo import fields, models


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    is_dashboard = fields.Boolean(string="Is Dashboard Menu")
    user_ids = fields.Many2many(
        "res.users", "menu_user_rel", "menu_id", "user_id", string="Users"
    )

    def _filter_visible_menus(self):
        """
        Filter menu base on user access
        """
        visible_ids = self._visible_menu_ids(
            request.session.debug if request else False
        )
        visible_ids = self.env["ir.ui.menu"].sudo().browse(visible_ids)
        user = self.env.user
        if user.has_group(
            "synconics_bi_dashboard.group_dashboard_user"
        ) and not user.has_group("synconics_bi_dashboard.group_dashboard_manager"):
            visible_ids = visible_ids.filtered(
                lambda menu: not menu.user_ids
                or (menu.user_ids and user.id in menu.user_ids.ids)
            )
        visible_ids = set(visible_ids.ids)
        return self.filtered(lambda menu: menu.id in visible_ids)
