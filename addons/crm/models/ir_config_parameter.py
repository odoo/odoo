# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class IrConfigParameter(models.Model):
    _inherit = 'ir.config_parameter'

    def write(self, vals):
        result = super().write(vals)
        if any(record.key == "crm.pls_fields" for record in self):
            # force the registry to update crm.lead.probability's depends
            self.flush()
            self.env.registry.setup_models(self.env.cr)
        return result

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if any(record.key == "crm.pls_fields" for record in records):
            # force the registry to update crm.lead.probability's depends
            self.flush()
            self.env.registry.setup_models(self.env.cr)
        return records
