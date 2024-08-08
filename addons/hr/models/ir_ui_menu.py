# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, tools


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def _load_menus_blacklist(self):
        res = super()._load_menus_blacklist()
        if self.env.user.has_group('hr.group_hr_user'):
            res.append(self.env.ref('hr.menu_hr_employee').id)
        else:
            is_department_manager = bool(self.env["hr.department"].search_count([
                ('manager_id', 'in', self.env.user.employee_ids.ids)
            ]))
            if not is_department_manager:
                res.append(self.env.ref('hr.menu_hr_department_kanban').id)
        return res
