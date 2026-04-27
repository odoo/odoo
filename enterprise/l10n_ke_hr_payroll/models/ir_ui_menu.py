# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def _load_menus_blacklist(self):
        res = super()._load_menus_blacklist()
        user_kenya_companies = self.env.user.company_ids.filtered(lambda c: c.country_id.code == 'KE')
        if not user_kenya_companies:
            res.append(self.env.ref('l10n_ke_hr_payroll.menu_l10n_ke_hr_payroll_nhif_report_wizard').id)
            res.append(self.env.ref('l10n_ke_hr_payroll.menu_l10n_ke_hr_payroll_nssf_report_wizard').id)
            res.append(self.env.ref('l10n_ke_hr_payroll.menu_l10n_ke_hr_payroll_master_report').id)
            res.append(self.env.ref('l10n_ke_hr_payroll.menu_reporting_l10n_ke').id)
        return res
