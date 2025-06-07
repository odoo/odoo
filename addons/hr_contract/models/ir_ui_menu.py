# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def _load_menus_blacklist(self):
        res = super()._load_menus_blacklist()
        is_contract_employee_manager = self.env.user.has_group('hr_contract.group_hr_contract_employee_manager')
        is_employee_officer = self.env.user.has_group('hr.group_hr_user')
        if not is_contract_employee_manager or is_employee_officer:
            res.append(self.env.ref('hr_contract.menu_hr_employee_contracts').id)
        return res
