# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def _load_menus_blacklist(self):
        res = super()._load_menus_blacklist()
        swiss_id = self.env.ref('base.ch', raise_if_not_found=False)
        user_swiss_companies = self.env.user.company_ids.filtered(lambda c: c.country_id == swiss_id)
        if user_swiss_companies:
            res.append(self.env.ref('hr_payroll.menu_hr_payroll_dashboard_root').id)
            res.append(self.env.ref('hr_payroll.menu_hr_payroll_employees_root').id)
            res.append(self.env.ref('hr_work_entry_contract_enterprise.menu_hr_payroll_work_entries_root').id)
            res.append(self.env.ref('hr_work_entry_contract_enterprise.menu_hr_work_entry_type_view').id)
            res.append(self.env.ref('hr_payroll.menu_hr_work_entry_report').id)
            res.append(self.env.ref('hr_payroll.menu_report_payroll').id)
        return res
