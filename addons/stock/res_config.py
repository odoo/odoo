# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv

class stock_config_settings(osv.osv_memory):
    _name = 'stock.config.settings'
    _inherit = 'res.config.settings'

    def set_group_stock_multi_locations(self, cr, uid, ids, context=None):
        """
            If we are not in multiple locations,
            we can deactivate the internal picking types of the warehouses.
            That way, they won't appear in the dashboard.
        """
        for obj in self.browse(cr, uid, ids, context=context):
            wh_obj = self.pool['stock.warehouse']
            whs = wh_obj.search(cr, uid, [], context=context)
            warehouses = wh_obj.browse(cr, uid, whs, context=context)
            if obj.group_stock_multi_locations:
                # Check inactive picking types and of warehouses make them active (by warehouse)
                inttypes = [x.int_type_id.id for x in warehouses if not x.int_type_id.active]
                if inttypes:
                    self.pool['stock.picking.type'].write(cr, uid, inttypes, {'active': True}, context=context)
            else:
                # Check active internal picking types of warehouses and make them inactive
                inttypes = [x.int_type_id.id for x in warehouses if x.int_type_id.active and x.reception_steps == 'one_step' and x.delivery_steps == 'ship_only']
                if inttypes:
                    self.pool['stock.picking.type'].write(cr, uid, inttypes, {'active': False}, context=context)
        return True

    def default_get(self, cr, uid, fields, context=None):
        res = super(stock_config_settings, self).default_get(cr, uid, fields, context=context)
        if 'warehouse_and_location_usage_level' in fields or not fields:
            res['warehouse_and_location_usage_level'] = int(res.get('group_stock_multi_locations', False)) + int(res.get('group_stock_multi_warehouses', False))
        return res

    def onchange_warehouse_and_location_usage_level(self, cr, uid, ids, level, context=None):
        return {'value': {
            'group_stock_multi_locations': level > 0,
            'group_stock_multi_warehouses': level > 1,
        }}

    _columns = {
        'group_product_variant': fields.selection([
            (0, "No variants on products"),
            (1, 'Products can have several attributes, defining variants (Example: size, color,...)')
            ], "Product Variants",
            help='Work with product variant allows you to define some variant of the same products, an ease the product management in the ecommerce for example',
            implied_group='product.group_product_variant'),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'module_procurement_jit': fields.selection([
            (1, 'Reserve products immediately after the sale order confirmation'),
            (0, 'Reserve products manually or based on automatic scheduler')
            ], "Procurements",
            help="""Allows you to automatically reserve the available
            products when confirming a sale order.
                This installs the module procurement_jit."""),
        'module_claim_from_delivery': fields.selection([
            (0, 'Do not manage claims'),
            (1, 'Allow claims on deliveries')
            ], "Claims",
            help='Adds a Claim link to the delivery order.\n'
                 '-This installs the module claim_from_delivery.'),
        'module_product_expiry': fields.selection([
            (0, 'Do not use Expiration Date on serial numbers'),
            (1, 'Define Expiration Date on serial numbers')
            ], "Expiration Dates",
            help="""Track different dates on products and serial numbers.
                    The following dates can be tracked:
                    - end of life
                    - best before date
                    - removal date
                    - alert date.
                    This installs the module product_expiry."""),
        'group_uom': fields.selection([
            (0, 'Products have only one unit of measure (easier)'),
            (1, 'Some products may be sold/purchased in different units of measure (advanced)')
            ], "Units of Measure",
            implied_group='product.group_uom',
            help="""Allows you to select and maintain different units of measure for products."""),
        'group_stock_packaging': fields.selection([
            (0, 'Do not manage packaging'),
            (1, 'Manage available packaging options per products')
            ], "Packaging Methods",
            implied_group='product.group_stock_packaging',
            help="""Allows you to create and manage your packaging dimensions and types you want to be maintained in your system."""),
        'group_stock_production_lot': fields.selection([
            (0, 'Do not track individual product items'),
            (1, 'Track lots or serial numbers')
            ], "Lots and Serial Numbers",
            implied_group='stock.group_production_lot',
            help="""This allows you to assign a lot (or serial number) to the pickings and moves.  This can make it possible to know which production lot was sent to a certain client, ..."""),
        'group_stock_tracking_lot': fields.selection([
            (0, 'Do not manage packaging'),
            (1, 'Record packages used on packing: pallets, boxes, ...')
            ], "Packages",
            implied_group='stock.group_tracking_lot',
            help="""This allows to manipulate packages.  You can put something in, take something from a package, but also move entire packages and put them even in another package.  """),
        'group_stock_tracking_owner': fields.selection([
            (0, 'All products in your warehouse belong to your company'),
            (1, 'Manage consignee stocks (advanced)')
            ], "Product Owners",
            implied_group='stock.group_tracking_owner',
            help="""This way you can receive products attributed to a certain owner. """),
        'group_stock_adv_location': fields.selection([
            (0, 'No automatic routing of products'),
            (1, 'Advanced routing of products using rules')
            ], "Routes",
            implied_group='stock.group_adv_location',
            help="""This option supplements the warehouse application by effectively implementing Push and Pull inventory flows through Routes."""),
        'decimal_precision': fields.integer('Decimal precision on weight', help="As an example, a decimal precision of 2 will allow weights like: 9.99 kg, whereas a decimal precision of 4 will allow weights like:  0.0231 kg."),
        'propagation_minimum_delta': fields.related('company_id', 'propagation_minimum_delta', type='integer', string="Minimum days to trigger a propagation of date change in pushed/pull flows."),
        'module_stock_dropshipping': fields.selection([
            (0, 'Suppliers always deliver to your warehouse(s)'),
            (1, "Allow suppliers to deliver directly to your customers")
            ], "Dropshipping",
            help='\nCreates the dropship route and add more complex tests\n'
                 '-This installs the module stock_dropshipping.'),
        'module_stock_picking_wave': fields.selection([
            (0, 'Manage pickings one at a time'),
            (1, 'Manage picking in batch per worker')
            ], "Picking Waves",
            help='Install the picking wave module which will help you grouping your pickings and processing them in batch'),
        'module_stock_calendar': fields.selection([
            (0, 'Set lead times in calendar days (easy)'),
            (1, "Adapt lead times using the suppliers' open days calendars (advanced)")
            ], "Minimum Stock Rules",
            help='This allows you to handle minimum stock rules differently by the possibility to take into account the purchase and delivery calendars \n-This installs the module stock_calendar.'),
        'module_stock_barcode': fields.boolean("Barcode scanner support"),
        'module_delivery_dhl': fields.boolean("DHL integration"),
        'module_delivery_fedex': fields.boolean("Fedex integration"),
        'module_delivery_temando': fields.boolean("Temando integration"),
        'module_delivery_ups': fields.boolean("UPS integration"),
        'module_delivery_usps': fields.boolean("USPS integration"),
        # Warehouse and location usage_level : 
        'warehouse_and_location_usage_level': fields.selection([
            (0, 'Manage only 1 Warehouse with only 1 stock location'),
            (1, 'Manage only 1 Warehouse, composed by several stock locations'),
            (2, 'Manage several Warehouses, each one composed by several stock locations')
            ], "Warehouses and Locations usage level"),
        'group_stock_multi_locations': fields.boolean('Manage several stock locations',
            implied_group='stock.group_stock_multi_locations'),
        'group_stock_multi_warehouses': fields.boolean('Manage several warehouses',
            implied_group='stock.group_stock_multi_warehouses'),
    }

    def onchange_adv_location(self, cr, uid, ids, group_stock_adv_location, context=None):
        if group_stock_adv_location:
            return {'value': {'warehouse_and_location_usage_level': 1}}
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
