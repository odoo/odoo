# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def _load_menus_blacklist(self):
        res = super()._load_menus_blacklist()
        if not self.env.user.has_group('helpdesk.group_helpdesk_manager'):
            res.append(self.env.ref('helpdesk.helpdesk_ticket_report_menu_ratings').id)
        return res
