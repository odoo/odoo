# -*- coding: utf-8 -*-

from functools import partial

from odoo import models, fields


class PosOrderReport(models.Model):
    _inherit = "report.pos.order"
    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True)

    def _select(self):
        return super()._select() + ',s.employee_id AS employee_id'

    def _group_by(self):
        group_by = super()._group_by()
        return (group_by + ',' if group_by else '') + 's.employee_id'
