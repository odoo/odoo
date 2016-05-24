# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import openerp
from openerp.osv import osv, fields


class resource_calendar(osv.osv):
    _inherit = "resource.calendar"
    _columns = {
        'uom_id': fields.many2one("product.uom", "Hours per Day", required=True,
            help="""Average hours of work per day.
                    It is used in an employee leave request to compute the number of days consumed based on the resource calendar.
                    It can be used to handle various contract types, e.g.:
                    - 38 Hours/Week, 5 Days/Week: 1 Day = 7.6 Hours
                    - 45 Hours/Week, 5 Days/Week: 1 Day = 9.0 Hours"""),
    }

    _defaults = {
        'uom_id': lambda self, cr, uid, c: self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'product.product_uom_hour')
    }


class resource_calendar_leaves(osv.osv):
    _inherit = "resource.calendar.leaves"
    _description = "Leave Detail"
    _columns = {
        'holiday_id': fields.many2one("hr.holidays", "Leave Request"),
    }
