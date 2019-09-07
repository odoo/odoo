# -*- coding: utf-8 -*-

from functools import partial

from odoo import models, fields


class PosConfig(models.Model):
    _inherit = 'pos.config'

    employee_ids = fields.Many2many(
        'hr.employee', string="Employees with access",
        help='If left empty, all employees can log in to the PoS session')
