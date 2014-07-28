# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2004-2012 OpenERP S.A. (<http://openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv
from openerp.tools.translate import _

class res_company(osv.osv):
    _inherit = "res.company"
    _columns = {
        'propagation_minimum_delta': fields.integer('Minimum Delta for Propagation of a Date Change on moves linked together'),
        'internal_transit_location_id': fields.many2one('stock.location', 'Internal Transit Location', help="Technical field used for resupply routes between warehouses that belong to this company", on_delete="restrict"),
    }

    def create_transit_location(self, cr, uid, company_id, company_name, context=None):
        '''Create a transit location with company_id being the given company_id. This is needed
           in case of resuply routes between warehouses belonging to the same company, because
           we don't want to create accounting entries at that time.
        '''
        data_obj = self.pool.get('ir.model.data')
        try:
            parent_loc = data_obj.get_object_reference(cr, uid, 'stock', 'stock_location_locations')[1]
        except:
            parent_loc = False
        location_vals = {
            'name': _('%s: Transit Location') % company_name,
            'usage': 'transit',
            'company_id': company_id,
            'location_id': parent_loc,
        }
        location_id = self.pool.get('stock.location').create(cr, uid, location_vals, context=context)
        self.write(cr, uid, [company_id], {'internal_transit_location_id': location_id}, context=context)

    def create(self, cr, uid, vals, context=None):
        company_id = super(res_company, self).create(cr, uid, vals, context=context)
        self.create_transit_location(cr, uid, company_id, vals['name'], context=context)
        return company_id

    _defaults = {
        'propagation_minimum_delta': 1,
    }

class stock_config_settings(osv.osv_memory):
    _name = 'stock.config.settings'
    _inherit = 'res.config.settings'

    _columns = {
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'module_procurement_jit': fields.boolean("Generate procurement in real time",
            help="""This allows Just In Time computation of procurement orders.
                All procurement orders will be processed immediately, which could in some
                cases entail a small performance impact.
                This installs the module procurement_jit."""),
        'module_claim_from_delivery': fields.boolean("Allow claim on deliveries",
            help='Adds a Claim link to the delivery order.\n'
                 '-This installs the module claim_from_delivery.'),
        'module_product_expiry': fields.boolean("Expiry date on serial numbers",
            help="""Track different dates on products and serial numbers.
The following dates can be tracked:
    - end of life
    - best before date
    - removal date
    - alert date.
This installs the module product_expiry."""),
        'group_uom': fields.boolean("Manage different units of measure for products",
            implied_group='product.group_uom',
            help="""Allows you to select and maintain different units of measure for products."""),
        'group_uos': fields.boolean("Store products in a different unit of measure than the sales order",
            implied_group='product.group_uos',
            help='Allows you to store units of a product, but sell and invoice based on a different unit of measure.\n'
                 'For instance, you can store pieces of meat that you sell and invoice based on their weight.'),
        'group_stock_packaging': fields.boolean("Allow to define several packaging methods on products",
            implied_group='product.group_stock_packaging',
            help="""Allows you to create and manage your packaging dimensions and types you want to be maintained in your system."""),
        'group_stock_production_lot': fields.boolean("Track lots or serial numbers",
            implied_group='stock.group_production_lot',
            help="""This allows you to assign a lot (or serial number) to the pickings and moves.  This can make it possible to know which production lot was sent to a certain client, ..."""),
        'group_stock_tracking_lot': fields.boolean("Use packages: pallets, boxes, ...",
            implied_group='stock.group_tracking_lot',
            help="""This allows to manipulate packages.  You can put something in, take something from a package, but also move entire packages and put them even in another package.  """),
        'group_stock_tracking_owner': fields.boolean("Manage owner on stock",
            implied_group='stock.group_tracking_owner',
            help="""This way you can receive products attributed to a certain owner. """),
        'group_stock_multiple_locations': fields.boolean("Manage multiple locations and warehouses",
            implied_group='stock.group_locations',
            help="""This will show you the locations and allows you to define multiple picking types and warehouses."""),
        'group_stock_adv_location': fields.boolean("Manage advanced routes for your warehouse",
            implied_group='stock.group_adv_location',
            help="""This option supplements the warehouse application by effectively implementing Push and Pull inventory flows through Routes."""),
        'decimal_precision': fields.integer('Decimal precision on weight', help="As an example, a decimal precision of 2 will allow weights like: 9.99 kg, whereas a decimal precision of 4 will allow weights like:  0.0231 kg."),
        'propagation_minimum_delta': fields.related('company_id', 'propagation_minimum_delta', type='integer', string="Minimum days to trigger a propagation of date change in pushed/pull flows."),
        'module_stock_dropshipping': fields.boolean("Manage dropshipping",
            help='\nCreates the dropship route and add more complex tests'
                 '-This installs the module stock_dropshipping.'),
        'module_stock_picking_wave': fields.boolean('Manage picking wave', help='Install the picking wave module which will help you grouping your pickings and processing them in batch'),
    }

    def onchange_adv_location(self, cr, uid, ids, group_stock_adv_location, context=None):
        if group_stock_adv_location:
            return {'value': {'group_stock_multiple_locations': True}}
        return {}

    def _default_company(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        return user.company_id.id

    def get_default_dp(self, cr, uid, fields, context=None):
        dp = self.pool.get('ir.model.data').get_object(cr, uid, 'product', 'decimal_stock_weight')
        return {'decimal_precision': dp.digits}

    def set_default_dp(self, cr, uid, ids, context=None):
        config = self.browse(cr, uid, ids[0], context)
        dp = self.pool.get('ir.model.data').get_object(cr, uid, 'product', 'decimal_stock_weight')
        dp.write({'digits': config.decimal_precision})

    _defaults = {
        'company_id': _default_company,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
