# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def _load_menus_blacklist(self):
        res = super()._load_menus_blacklist()
        job_menu = self.env.ref('hr_recruitment.menu_hr_job_position', raise_if_not_found=False)
        int_menu = self.env.ref('hr_recruitment.menu_hr_job_position_interviewer', raise_if_not_found=False)
        if job_menu and self.env.user.has_group('hr_recruitment.group_hr_recruitment_interviewer') and not self.env.user.has_group('hr_recruitment.group_hr_recruitment_user'):
            res.append(job_menu.id)
        elif int_menu and self.env.user.has_group('hr_recruitment.group_hr_recruitment_user'):
            res.append(int_menu.id)
        return res
