# -*- coding: utf-8 -*-

from functools import partial

from odoo import models, fields


class PosOrderReport(models.Model):
    _inherit = "report.pos.order"
    cashier_id = fields.Many2one('hr.employee', string='Employee', readonly=True)

    def _select(self):
        return super()._select() + ',s.cashier_id AS cashier_id'

    def _group_by(self):
        return super()._group_by() + ',s.cashier_id'
