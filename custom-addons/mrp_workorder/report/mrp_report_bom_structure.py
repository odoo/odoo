# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import float_round


class ReportBomStructure(models.AbstractModel):
    _inherit = 'report.mrp.report_bom_structure'

    def _get_operation_cost(self, duration, operation):
        employee_cost = (duration / 60.0) * operation.workcenter_id.employee_costs_hour * operation.employee_ratio
        return super()._get_operation_cost(duration, operation) + employee_cost

    @api.model
    def _get_operation_line(self, product, bom, qty, level, index):
        operations_list = super()._get_operation_line(product, bom, qty, level, index)

        for operation_item in operations_list:
            operation = operation_item['operation']
            capacity = operation.workcenter_id._get_capacity(product)
            operation_cycle = float_round(qty / capacity, precision_rounding=1, rounding_method='UP')
            workcenter_capacity_ids = operation.workcenter_id.capacity_ids.filtered(lambda x: x.product_id == product)[:-1]
            if workcenter_capacity_ids:
                product_specific_setup_cleanup_time = (workcenter_capacity_ids.time_start + workcenter_capacity_ids.time_stop)
                workcenter_time = (operation_cycle * operation.time_cycle * 100.0 / operation.workcenter_id.time_efficiency)
                operation_item['quantity'] = workcenter_time + product_specific_setup_cleanup_time
            product_specific_setup_cleanup_time = 0

        return operations_list
