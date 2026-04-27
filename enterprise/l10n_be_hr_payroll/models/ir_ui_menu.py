# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def _load_menus_blacklist(self):
        res = super()._load_menus_blacklist()
        belgium_id = self.env.ref('base.be', raise_if_not_found=False)
        user_belgium_companies = self.env.user.company_ids.filtered(lambda c: c.country_id == belgium_id)
        if not user_belgium_companies:
            res.append(self.env.ref('l10n_be_hr_payroll.menu_reporting_l10n_be').id)
        return res
