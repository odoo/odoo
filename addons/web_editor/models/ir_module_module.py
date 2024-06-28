# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrModuleModule(models.Model):
    _name = "ir.module.module"
    _description = 'Module'
    _inherit = _name

    def module_uninstall(self):
        result = super().module_uninstall()
        self.env['web_editor.edited']._clean()
        return result
