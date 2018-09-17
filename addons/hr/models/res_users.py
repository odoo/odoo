# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class User(models.Model):
    _inherit = ['res.users']

    employee_ids = fields.One2many('hr.employee', 'user_id', string='Related employees')

    @api.multi
    def write(self, vals):
        """ Synchronize user and its related employee """
        result = super(User, self).write(vals)
        employee_values = {}
        for fname in [f for f in ['name', 'email', 'image', 'tz'] if f in vals]:
            employee_values[fname] = vals[fname]
        if employee_values:
            self.env['hr.employee'].sudo().search([('user_id', 'in', self.ids)]).write(employee_values)
        return result
