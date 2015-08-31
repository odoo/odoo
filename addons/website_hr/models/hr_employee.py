# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class HrEmployee(models.Model):
    _name = 'hr.employee'
    _inherit = ['hr.employee', 'website.published.mixin']

    public_info = fields.Char(string='Public Info')

    @api.multi
    def _website_url(self, field_name, arg):
        res = super(HrEmployee, self)._website_url(field_name, arg)
        res.update({(employee_id, '/page/website.aboutus#team') for employee_id in self.ids})
        return res
