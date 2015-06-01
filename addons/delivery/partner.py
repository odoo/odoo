# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv

class res_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'property_delivery_carrier': fields.property(
          type='many2one',
          relation='delivery.carrier',
          string="Delivery Method",
          help="This delivery method will be used when invoicing from picking."),
    }
