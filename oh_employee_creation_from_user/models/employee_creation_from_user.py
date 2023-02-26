# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ResUsersInherit(models.Model):
    _inherit = 'res.users'

    employee_id = fields.Many2one('hr.employee',
                                  string='Related Employee', ondelete='restrict', auto_join=True,
                                  help='Employee-related data of the user')

    @api.model
    def create(self, vals):
        """This code is to create an employee while creating an user."""

        result = super(ResUsersInherit, self).create(vals)
        result['employee_id'] = self.env['hr.employee'].sudo().create({'name': result['name'],
                                                                       'user_id': result['id'],
                                                                       'address_home_id': result['partner_id'].id})
        return result
