# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class IrConfig_Parameter(models.Model):
    _inherit = 'ir.config_parameter'

    def write(self, vals):
        result = super().write(vals)
        if any(record.key == "crm.pls_fields" for record in self):
            self.env.flush_all()
            self.env.registry._setup_models__(self.env.cr, ['crm.lead'])
        return result

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if any(record.key == "crm.pls_fields" for record in records):
            self.env.flush_all()
            self.env.registry._setup_models__(self.env.cr, ['crm.lead'])
        return records

    def unlink(self):
        pls_emptied = any(record.key == "crm.pls_fields" for record in self)
        result = super().unlink()
        if pls_emptied and not self.pool.uninstalling_modules:
            self.env.flush_all()
            self.env.registry._setup_models__(self.env.cr, ['crm.lead'])
        return result
