# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields
from odoo import SUPERUSER_ID


class User(models.Model):

    _inherit = ['res.users']

    employee_ids = fields.One2many('hr.employee', 'user_id', string='Related employees')

    @api.multi
    def write(self, vals):
        """ When renaming admin user, we want its new name propagated to its related employees """
        result = super(User, self).write(vals)
        Employee = self.env['hr.employee']
        if vals.get('name'):
            for user in self.filtered(lambda user: user.id == SUPERUSER_ID):
                employees = Employee.search([('user_id', '=', user.id)])
                employees.write({'name': vals['name']})
        return result
