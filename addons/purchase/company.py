# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv,fields

class company(osv.osv):
    _inherit = 'res.company'
    _columns = {
        'po_lead': fields.float(
            'Purchase Lead Time', required=True,
            help="Margin of error for supplier lead times. When the system "\
                 "generates Purchase Orders for procuring products, "\
                 "they will be scheduled that many days earlier "\
                 "to cope with unexpected supplier delays."),
    }
    _defaults = {
        'po_lead': lambda *a: 1.0,
    }
