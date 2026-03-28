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

