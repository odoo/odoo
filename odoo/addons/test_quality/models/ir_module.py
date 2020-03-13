# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _

class IrModule(models.Model):
    _inherit = 'ir.module.module'

    required_module_ids = fields.Many2many("ir.module.module", compute="_compute_required_module_ids")

    def _compute_required_module_ids(self):
        for module in self:
            module.required_module_ids = module.dependencies_id.depend_id | module.dependencies_id.depend_id.required_module_ids