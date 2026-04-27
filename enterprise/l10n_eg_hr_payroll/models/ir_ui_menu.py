# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def _load_menus_blacklist(self):
        res = super()._load_menus_blacklist()
        if 'EG' not in self.env.companies.mapped('country_code'):
            res.append(self.env.ref('l10n_eg_hr_payroll.menu_reporting_l10n_eg').id)
        return res
