# -*- coding: utf-8 -*-
from odoo import models


class IrModuleModule(models.Model):
    _inherit = 'ir.module.module'

    def module_uninstall(self):
        helpdesk_modules = self.env['helpdesk.team']._get_field_modules()
        modules_field = {module: field for field, module in helpdesk_modules.items()}
        fields_to_reset = [modules_field[name] for name in self.mapped('name') if name in modules_field.keys()]
        if fields_to_reset:
            update_sql = ', '.join([f"{field} = FALSE" for field in fields_to_reset])
            query = f"UPDATE helpdesk_team SET {update_sql}"
            self.env.cr.execute(query)

        return super().module_uninstall()
