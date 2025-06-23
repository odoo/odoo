# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, tools


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def _load_menus_blacklist(self):
        res = super()._load_menus_blacklist()
        emp_menu = self.env.ref('hr.menu_hr_employee', raise_if_not_found=False)
        if emp_menu and self.env.user.has_group('hr.group_hr_user'):
            res.append(emp_menu.id)
        return res
