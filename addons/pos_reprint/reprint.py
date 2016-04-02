# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import openerp
from openerp.osv import fields, osv

class pos_config(osv.osv):
    _inherit = 'pos.config' 
    _columns = {
        'iface_reprint': fields.boolean('Receipt Reprinting', help="This allows you to reprint a previously printed receipt."),
        }
    _defaults = {
        'iface_reprint': False,
    }
