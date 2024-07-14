# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class L10nChHrEmployeeChildren(models.Model):
    _name = 'l10n.ch.hr.employee.children'
    _description = 'Employee Children'

    employee_id = fields.Many2one('hr.employee')
    name = fields.Char("Complete Name", required=True)
    birthdate = fields.Date(required=True)
    deduction_start = fields.Date(
        required=True, compute='_compute_deduction_start', store=True, readonly=False,
        help="Beginning of the right to the child deduction")

    @api.depends('birthdate')
    def _compute_deduction_start(self):
        for child in self:
            if not child.birthdate or child.deduction_start:
                continue
            child.deduction_start = child.birthdate
