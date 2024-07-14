# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def _load_menus_blacklist(self):
        res = super()._load_menus_blacklist()
        india_id = self.env.ref('base.in', raise_if_not_found=False)
        user_indian_companies = self.env.user.company_ids.filtered(lambda c: c.country_id == india_id)
        if not user_indian_companies:
            res.append(self.env.ref('l10n_in_hr_payroll.hr_menu_payment_advice').id)
        return res
