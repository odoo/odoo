# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def _load_menus_blacklist(self):
        res = super()._load_menus_blacklist()
        if not self.env.user.has_group('industry_fsm.group_fsm_manager'):
            res.append(self.env.ref('industry_fsm.fsm_menu_reporting_customer_ratings').id)
        return res
