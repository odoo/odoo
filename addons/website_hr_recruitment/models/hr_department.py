# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class hr_department(osv.osv):
    _inherit = "hr.department"
    _columns = {
        # add field for access right
        'department_ids': fields.one2many('hr.job', 'department_id', 'Department'),
    }