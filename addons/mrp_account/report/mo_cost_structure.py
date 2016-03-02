# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models
from openerp.report import report_sxw
from itertools import groupby


class mo_cost_structure(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(mo_cost_structure, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'get_workorders': self.get_workorders,
            'get_total_cost': self.get_total_cost,
        })

    def get_workorders(self, orders):
        result = []
        for order in orders:
            res = {}
            time_data = order.time_ids.read_group([('workorder_id', '=', order.id)], ['duration', 'user_id'], 'user_id')
            res['name'] = order.name
            res['cost'] = order.workcenter_id.costs_hour
            res['lines'] = [{'operator': record['user_id'][1], 'duration': round(record['duration'] / 60, 2)} for record in time_data]
            result.append(res)
        return result

    def get_total_cost(self, order):
        total_cost = 0.0
        for raw in order.move_raw_ids:
            total_cost += raw.product_uom_qty * raw.product_id.standard_price
        for workorder in order.work_order_ids:
            total_cost += (sum(workorder.time_ids.mapped('duration')) / 60) * workorder.workcenter_id.costs_hour
        return round(total_cost, 2)


class report_mocoststructure(models.AbstractModel):
    _name = 'report.mrp_account.report_mocoststructure'
    _inherit = 'report.abstract_report'
    _template = 'mrp_account.report_mocoststructure'
    _wrapped_report_class = mo_cost_structure
