# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class res_users(osv.osv):
    _inherit = 'res.users'
    _columns = {
        'target_sales_invoiced': fields.integer('Invoiced in Sale Orders Target'),
    }
