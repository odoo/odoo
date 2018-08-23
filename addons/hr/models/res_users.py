# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields
from odoo import SUPERUSER_ID


class User(models.Model):

    _inherit = ['res.users']

    employee_ids = fields.One2many('hr.employee', 'user_id', string='Related employees')

    group_hr_user = fields.Selection(
        selection=lambda self: self._get_group_selection('base.module_category_human_resources'),
        string="Human Resources", compute='_compute_groups_id', inverse='_inverse_groups_id',
        category_xml_id='base.module_category_human_resources',
        help='Officer: The user will be able to approve document created by employees.\nManager: The user will have access to the human resources configuration as well as statistic reports.')

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
