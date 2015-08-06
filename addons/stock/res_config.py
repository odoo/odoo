# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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

    def set_group_locations(self, cr, uid, ids, context=None):
        """ This method is automatically called by res_config as it begins
            with set. It is used to implement the 'one group or another'
            behavior. We have to perform some group manipulation by hand
            because in res_config.execute(), set_* methods are called
            after group_*; therefore writing on an hidden res_config file
            could not work.
            If group_stock_multiple_locations is checked: remove group_stock_single_location
            from group_user, remove the users. Otherwise, just add
            group_stock_single_location in group_user.
            The inverse logic about group_stock_multiple_locations is managed by the
            normal behavior of 'group_stock_multiple_locations' field.
        """
        def ref(xml_id):
            mod, xml = xml_id.split('.', 1)
            return self.pool['ir.model.data'].get_object(cr, uid, mod, xml, context)

        for obj in self.browse(cr, uid, ids, context=context):
            config_group = ref('stock.group_single_location')
            base_group = ref('base.group_user')
            if obj.group_stock_multiple_locations:
                base_group.write({'implied_ids': [(3, config_group.id)]})
                config_group.write({'users': [(3, u.id) for u in base_group.users]})
            else:
                base_group.write({'implied_ids': [(4, config_group.id)]})
        return True

    _columns = {
        'group_product_variant': fields.selection([
            (0, "No variants on products"),
            (1, 'Products can have several attributes, defining variants (Example: size, color,...)')
            ], "Product Variants",
            help='Work with product variant allows you to define some variant of the same products, an ease the product management in the ecommerce for example',
            implied_group='product.group_product_variant'),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'module_procurement_jit': fields.selection([
            (1, 'Schedule orders in real time'),
            (0, 'Run scheduler once a day')
            ], "Procurements",
            help="""This allows Just In Time computation of procurement orders.
                All procurement orders will be processed immediately, which could in some
                cases entail a small performance impact.
                This installs the module procurement_jit."""),
        'module_claim_from_delivery': fields.selection([
            (0, 'Do not manage claims'),
            (1, 'Allow claims on deliveries')
            ], "Claims",
            help='Adds a Claim link to the delivery order.\n'
                 '-This installs the module claim_from_delivery.'),
        'module_product_expiry': fields.selection([
            (0, 'Do not use expiry date'),
            (1, 'Define expiry date on serial numbers')
            ], "Expiry Dates",
            help="""Track different dates on products and serial numbers.
                    The following dates can be tracked:
                    - end of life
                    - best before date
                    - removal date
                    - alert date.
                    This installs the module product_expiry."""),
        'group_uom': fields.selection([
            (0, 'Products have only one unit of measure (easier)'),
            (1, 'Some products may be sold/purchased in different unit of measures (advanced)')
            ], "Unit of Measures",
            implied_group='product.group_uom',
            help="""Allows you to select and maintain different units of measure for products."""),
        'group_uos': fields.selection([
            (0, 'Use the same product unit of measure in the stocks than in the sales order'),
            (1, 'Store products in a different unit of measure than the sales order')
            ], "Unit of Sales",
            implied_group='product.group_uos',
            help='Allows you to store units of a product, but sell and invoice based on a different unit of measure.\n'
                 'For instance, you can store pieces of meat that you sell and invoice based on their weight.'),
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
            (1, 'Record packages used on packing: pallets, boxes, ...)')
            ], "Packages",
            implied_group='stock.group_tracking_lot',
            help="""This allows to manipulate packages.  You can put something in, take something from a package, but also move entire packages and put them even in another package.  """),
        'group_stock_tracking_owner': fields.selection([
            (0, 'All products in your warehouse belong to your company'),
            (1, 'Manage consignee stocks (advanced)')
            ], "Product Owners",
            implied_group='stock.group_tracking_owner',
            help="""This way you can receive products attributed to a certain owner. """),
        'group_stock_multiple_locations': fields.selection([
            (0, 'Do not record internal moves within a warehouse'),
            (1, 'Manage several locations per warehouse')
            ], "Multi Locations",
            implied_group='stock.group_locations',
            help="""This will show you the locations and allows you to define multiple picking types and warehouses."""),
        'group_stock_single_location': fields.boolean("Manage only one location per warehouse",
            implied_group='stock.group_single_location',
            help="""This implies that you manage one location per warehouse, i.e. no internal transfer is possible."""),
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
            help='\nCreates the dropship route and add more complex tests'
                 '-This installs the module stock_dropshipping.'),
        'module_stock_picking_wave': fields.selection([
            (0, 'Manage pickings one at a time'),
            (1, 'Manage picking in batch per worker')
            ], "Picking Waves",
            help='Install the picking wave module which will help you grouping your pickings and processing them in batch'),
        'module_stock_calendar': fields.selection([
            (0, 'Set lead times in calendar days (easy)'),
            (1, "Adapt lead times using the suppliers' open days calendars (advanced)")
            ], "Minimun Stock Rules",
            help='This allows you to handle minimum stock rules differently by the possibility to take into account the purchase and delivery calendars \n-This installs the module stock_calendar.'),
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
