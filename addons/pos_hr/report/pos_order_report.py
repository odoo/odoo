# -*- coding: utf-8 -*-

from functools import partial

from odoo import models, fields


class PosOrderReport(models.Model):
    _inherit = "report.pos.order"
    employee_id = fields.Many2one(
                'hr.employee', string='Employee', readonly=True)

    def _select(self):
        return super(PosOrderReport, self)._select() + ',s.employee_id AS employee_id'

    def _group_by(self):
        return super(PosOrderReport, self)._group_by() + ',s.employee_id'
