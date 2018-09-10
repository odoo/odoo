# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class User(models.Model):
    _inherit = ['res.users']

    employee_ids = fields.One2many('hr.employee', 'user_id', string='Related employees')

    group_hr_user = fields.Selection(
        selection=lambda self: self._get_group_selection('base.module_category_human_resources'),
        string="Employees", compute='_compute_groups_id', inverse='_inverse_groups_id',
        category_xml_id='base.module_category_human_resources',
        help='Officer: The user will be able to approve document created by employees.\nManager: The user will have access to the human resources configuration as well as statistic reports.')

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
