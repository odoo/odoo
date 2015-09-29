# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, models


class MrpOperations(models.Model):
    _name = "mrp_operations.operation"

    @api.model
    def initialize_workflow_instance(self):
        MrpProductionWorkcenterLine = self.env['mrp.production.workcenter.line']
        line_ids = MrpProductionWorkcenterLine.search([])
        line_ids.create_workflow()
        return True
