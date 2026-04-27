# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ReportBomStructure(models.AbstractModel):
    _inherit = 'report.mrp.report_bom_structure'

    def _get_operation_cost(self, operation, workcenter, duration):
        employee_cost = (duration / 60.0) * operation.employee_ratio * workcenter.employee_costs_hour
        return super()._get_operation_cost(operation, workcenter, duration) + employee_cost
