# -*- coding: utf-8 -*-

import re

from odoo import api, fields, models, tools, _

MENU_ITEM_SEPARATOR = "/"
NUMBER_PARENS = re.compile(r"\(([0-9]+)\)")


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def _get_full_name(self, level=6):
        """ Return the full name of ``self`` (up to a certain level). """
        if level <= 0:
            return '...'
        if self.parent_id:
            try:
                name = self.parent_id._get_full_name(level - 1) + MENU_ITEM_SEPARATOR + (self.name or "")
            except Exception:
                name = self.name or "..."
        else:
            name = self.name
        return name

    def load_web_menus(self, debug):
        web_menus = super(IrUiMenu, self).load_web_menus(debug)
        if debug:
            menus = self.load_menus(debug)  # This method has been cached in ORM and does not affect the performance
            for menu_id in web_menus.keys():
                if menu_id == 'root':
                    web_menus[menu_id]['sequence'] = 0
                    continue
                web_menus[menu_id]['sequence'] = menus[menu_id]['sequence']
        return web_menus