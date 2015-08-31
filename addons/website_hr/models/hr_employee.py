# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class hr_employee(osv.osv):
    _name = 'hr.employee'
    _inherit = ['hr.employee', 'website.published.mixin']

    _columns = {
        'public_info': fields.char('Public Info'),
    }

    def _website_url(self, cr, uid, ids, field_name, arg, context=None):
        res = super(hr_employee, self)._website_url(cr, uid, ids, field_name, arg, context=context)
        res.update({(employee_id, '/page/website.aboutus#team') for employee_id in ids})
        return res
