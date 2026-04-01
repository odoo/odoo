# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, tools
from odoo.http import request


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    @tools.ormcache('self.env.uid', 'self.env.lang', 'self.env.context.get("force_action")')
    def load_menus_root(self):
        root_menus = super().load_menus_root()
        if self.env.context.get('force_action'):
            web_menus = self.load_web_menus(request.session.debug if request else False)
            for menu in root_menus['children']:
                # Force the action.
                if (
                    not menu['action']
                    and web_menus[menu['id']]['actionModel']
                    and web_menus[menu['id']]['actionID']
                ):
                    menu['action'] = f"{web_menus[menu['id']]['actionModel']},{web_menus[menu['id']]['actionID']}"

        return root_menus
