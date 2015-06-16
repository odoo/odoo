# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv,fields

class company(osv.osv):
    _inherit = 'res.company'
    _columns = {
        'manufacturing_lead': fields.float('Manufacturing Lead Time', required=True,
            help="Security days for each manufacturing operation."),
    }
    _defaults = {
        'manufacturing_lead': lambda *a: 1.0,
    }
