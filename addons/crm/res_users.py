# -*- coding: utf-8 -*-

from openerp.osv import osv, fields

import openerp.addons.product.product


class res_users(osv.osv):
    _inherit = 'res.users'
    _columns = {
        'target_sales_won': fields.integer('Target of won opportunities'),
        'target_sales_done': fields.integer('Target of activities done'),
        'target_sales_invoiced': fields.integer('Target of invoiced sale orders'),
    }
