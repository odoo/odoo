# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models

class IrModuleModule(models.Model):
    _inherit = 'ir.module.module'

    def button_uninstall(self):
        extra = self.browse()
        if any(m.name == 'timesheet_grid' for m in self):
            extra = self.env['ir.module.module'].search([
                ('name', 'in', ['hr_timesheet', 'sale_timesheet']),
                ('state', 'in', ['installed', 'to upgrade']),
            ])
        return super(IrModuleModule, (self | extra)).button_uninstall()
