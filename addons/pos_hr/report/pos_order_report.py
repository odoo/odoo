# -*- coding: utf-8 -*-

from functools import partial

from odoo import models, fields
from odoo.addons import point_of_sale


class ReportPosOrder(point_of_sale.ReportPosOrder):
    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True)

    def _select(self):
        return super()._select() + ',s.employee_id AS employee_id'

    def _group_by(self):
        return super()._group_by() + ',s.employee_id'
