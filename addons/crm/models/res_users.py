# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class res_users(osv.osv):
    _inherit = 'res.users'
    _columns = {
        'target_sales_won': fields.integer('Won in Opportunities Target'),
        'target_sales_done': fields.integer('Activities Done Target'),
    }
