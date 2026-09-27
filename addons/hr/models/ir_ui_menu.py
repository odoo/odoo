# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def _load_menus_blacklist(self):
        res = super()._load_menus_blacklist()
        if not self.env.user.has_group('hr.group_hr_user'):
            is_department_manager = bool(self.env["hr.department"].search_count([
                ('manager_id', 'in', self.env.user.employee_ids.ids)
            ], limit=1))
            if not is_department_manager and (dep_menu := self.env.ref('hr.menu_hr_department_kanban', raise_if_not_found=False)):
                res.append(dep_menu.id)
        return res
