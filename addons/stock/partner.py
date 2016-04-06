# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.addons.base.res.res_partner import WARNING_MESSAGE, WARNING_HELP

class res_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'property_stock_customer': fields.property(
          type='many2one',
          relation='stock.location',
          string="Customer Location",
          help="This stock location will be used, instead of the default one, as the destination location for goods you send to this partner"),
        'property_stock_supplier': fields.property(
          type='many2one',
          relation='stock.location',
          string="Vendor Location",
          help="This stock location will be used, instead of the default one, as the source location for goods you receive from the current partner"),
        'picking_warn' : fields.selection(WARNING_MESSAGE, 'Stock Picking', help=WARNING_HELP, required=True),
        'picking_warn_msg' : fields.text('Message for Stock Picking'),
    }

    _defaults = {
        'picking_warn': 'no-message',
    }
