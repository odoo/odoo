# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import openerp
from openerp import SUPERUSER_ID
from openerp.osv import fields, osv
from openerp.tools.translate import _

class sale_configuration(osv.osv_memory):
    _inherit = 'sale.config.settings'

    _columns = {
        'default_order_policy': fields.selection([
                ('manual', 'Invoice based on sales order'),
                ('picking', 'Invoice based on delivery orders')],
            'Invoicing Method', default_model='sale.order'),
        'module_delivery': fields.selection([
            (0, 'No shipping costs on sales orders'),
            (1, 'Allow adding shipping costs')
            ], "Shipping"),
        'default_picking_policy' : fields.selection([
            (0, 'Ship products when some are available, and allow back orders'),
            (1, 'Ship all products at once, without back orders')
            ], "Default Shipping Policy"),
        'group_mrp_properties': fields.selection([
            (0, "Don't use manufacturing properties (recommended as its easier)"),
            (1, 'Allow setting manufacturing order properties per order line (avanced)')
            ], "Properties on SO Lines",
            implied_group='sale.group_mrp_properties',
            help="Allows you to tag sales order lines with properties."),
        'group_route_so_lines': fields.selection([
            (0, 'No order specific routes like MTO or drop shipping'),
            (1, 'Choose specific routes on sales order lines (advanced)')
            ], "Order Routing",
            implied_group='sale_stock.group_route_so_lines'),
    }

    _defaults = {
        'default_order_policy': 'manual',
    }

    def get_default_sale_config(self, cr, uid, ids, context=None):
        ir_values = self.pool.get('ir.values')
        default_picking_policy = ir_values.get_default(cr, uid, 'sale.order', 'picking_policy')
        return {
            'default_picking_policy': (default_picking_policy == 'one') and 1 or 0,
        }

    def set_sale_defaults(self, cr, uid, ids, context=None):
        if not self.pool['res.users']._is_admin(cr, uid, [uid]):
            raise openerp.exceptions.AccessError(_("Only administrators can change the settings"))
        ir_values = self.pool.get('ir.values')
        wizard = self.browse(cr, uid, ids)[0]

        default_picking_policy = 'one' if wizard.default_picking_policy else 'direct'
        ir_values.set_default(cr, SUPERUSER_ID, 'sale.order', 'picking_policy', default_picking_policy)
        res = super(sale_configuration, self).set_sale_defaults(cr, uid, ids, context)
        return res

