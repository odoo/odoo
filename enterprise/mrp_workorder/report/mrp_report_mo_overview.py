# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class ReportMoOverview(models.AbstractModel):
    _inherit = 'report.mrp.report_mo_overview'

    def _get_finished_operation_data(self, production, level=0, current_index=False):
        res = super()._get_finished_operation_data(production, level, current_index)
        currency = res['summary']['currency']
        done_operation_uom = res['summary']['uom_name']
        operations = res['details']
        index = 0
        for workorder in production.workorder_ids:
            for employee, time_ids in workorder.time_ids.grouped('employee_id').items():
                if not employee:
                    continue
                for times in time_ids.grouped('employee_cost').values():
                    hourly_cost = times[0].employee_cost
                    duration = sum(times.mapped('duration'))
                    operation_cost = duration / 60 * hourly_cost
                    mo_cost = workorder._get_current_theorical_employee_cost()
                    res['summary']['mo_cost'] += mo_cost
                    res['summary']['real_cost'] += operation_cost
                    operations.append({
                        'level': level,
                        'index': f"{current_index}WE{index}",
                        'name': f"{employee.display_name}: {workorder.display_name}",
                        'quantity': duration / 60,
                        'uom_name': done_operation_uom,
                        'uom_precision': 4,
                        'unit_cost': hourly_cost,
                        'mo_cost': currency.round(mo_cost),
                        'real_cost_decorator': self._get_comparison_decorator(mo_cost, operation_cost, currency.rounding),
                        'bom_cost': False,
                        'real_cost': currency.round(operation_cost),
                        'currency_id': currency.id,
                        'currency': currency,
                    })
                    index += 1
        res['summary']['real_cost_decorator'] = self._get_comparison_decorator(res['summary']['mo_cost'], res['summary']['real_cost'], currency.rounding)
        return res
