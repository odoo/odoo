# -*- coding: utf-8 -*-

from openerp import api
from openerp.osv import osv, fields


class hr_employee(osv.osv):
    _name = 'hr.employee'
    _inherit = ['hr.employee', 'website.published.mixin']

    _columns = {
        'public_info': fields.text('Public Info'),
    }

    @api.multi
    @api.depends('name')
    def _website_url(self):
        super(hr_employee, self)._website_url()
        for employee in self:
            employee.website_url = '/page/website.aboutus#team'
