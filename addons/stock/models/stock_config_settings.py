# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockSettings(models.TransientModel):
    _name = 'stock.config.settings'
    _inherit = 'res.config.settings'

    @api.model
    def default_get(self, fields):
        res = super(StockSettings, self).default_get(fields)
        if 'warehouse_and_location_usage_level' in fields or not fields:
            res['warehouse_and_location_usage_level'] = int(res.get('group_stock_multi_locations', False)) + int(res.get('group_stock_multi_warehouses', False))
        return res

    group_product_variant = fields.Selection([
        (0, "No variants on products"),
        (1, 'Products can have several attributes, defining variants (Example: size, color,...)')
        ], "Product Variants",
        implied_group='product.group_product_variant',
        help='Work with product variant allows you to define some variant of the same products, an ease the product management in the ecommerce for example')
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env.user.company_id, required=True)
    module_procurement_jit = fields.Selection([
        (1, 'Reserve products immediately after the sale order confirmation'),
        (0, 'Reserve products manually or based on automatic scheduler')
        ], "Procurements",
        help="""Allows you to automatically reserve the available
        products when confirming a sale order.
            This installs the module procurement_jit.""")
    module_product_expiry = fields.Selection([
        (0, 'Do not use Expiration Date on serial numbers'),
        (1, 'Define Expiration Date on serial numbers')
        ], "Expiration Dates",
        help="""Track different dates on products and serial numbers.
                The following dates can be tracked:
                - end of life
                - best before date
                - removal date
                - alert date.
                This installs the module product_expiry.""")
    group_uom = fields.Selection([
        (0, 'Products have only one unit of measure (easier)'),
        (1, 'Some products may be sold/purchased in different units of measure (advanced)')
        ], "Units of Measure",
        implied_group='product.group_uom',
        help="""Allows you to select and maintain different units of measure for products.""")
    group_stock_packaging = fields.Selection([
        (0, 'Do not manage packaging'),
        (1, 'Manage available packaging options per products')
        ], "Packaging Methods",
        implied_group='product.group_stock_packaging',
        help="""Allows you to create and manage your packaging dimensions and types you want to be maintained in your system.""")
    group_stock_production_lot = fields.Selection([
        (0, 'Do not track individual product items'),
        (1, 'Track lots or serial numbers')
        ], "Lots and Serial Numbers",
        implied_group='stock.group_production_lot',
        help="""This allows you to assign a lot (or serial number) to the pickings and moves.  This can make it possible to know which production lot was sent to a certain client, ...""")
    group_stock_tracking_lot = fields.Selection([
        (0, 'Do not manage packaging'),
        (1, 'Record packages used on packing: pallets, boxes, ...')
        ], "Packages",
        implied_group='stock.group_tracking_lot',
        help="""This allows to manipulate packages.  You can put something in, take something from a package, but also move entire packages and put them even in another package.  """)
    group_stock_tracking_owner = fields.Selection([
        (0, 'All products in your warehouse belong to your company'),
        (1, 'Manage consignee stocks (advanced)')
        ], "Product Owners",
        implied_group='stock.group_tracking_owner',
        help="""This way you can receive products attributed to a certain owner. """)
    group_stock_adv_location = fields.Selection([
        (0, 'No automatic routing of products'),
        (1, 'Advanced routing of products using rules')
        ], "Routes",
        implied_group='stock.group_adv_location',
        help="""This option supplements the warehouse application by effectively implementing Push and Pull inventory flows through Routes.""")
    group_warning_stock = fields.Selection([
        (0, 'All the partners can be used in pickings'),
        (1, 'An informative or blocking warning can be set on a partner')
        ], "Warning", implied_group='stock.group_warning_stock')
    decimal_precision = fields.Integer('Decimal precision on weight', help="As an example, a decimal precision of 2 will allow weights like: 9.99 kg, whereas a decimal precision of 4 will allow weights like:  0.0231 kg.")
    propagation_minimum_delta = fields.Integer("Minimum days to trigger a propagation of date change in pushed/pull flows.", related='company_id.propagation_minimum_delta')
    module_stock_dropshipping = fields.Selection([
        (0, 'Suppliers always deliver to your warehouse(s)'),
        (1, "Allow suppliers to deliver directly to your customers")
        ], "Dropshipping",
        help='\nCreates the dropship route and add more complex tests\n'
             '-This installs the module stock_dropshipping.')
    module_stock_picking_wave = fields.Selection([
        (0, 'Manage pickings one at a time'),
        (1, 'Manage picking in batch per worker')
        ], "Picking Waves",
        help='Install the picking wave module which will help you grouping your pickings and processing them in batch')
    module_stock_calendar = fields.Selection([
        (0, 'Set lead times in calendar days (easy)'),
        (1, "Adapt lead times using the suppliers' open days calendars (advanced)")
        ], "Minimum Stock Rules",
        help='This allows you to handle minimum stock rules differently by the possibility to take into account the purchase and delivery calendars \n-This installs the module stock_calendar.')
    module_stock_barcode = fields.Boolean("Barcode scanner support")
    module_delivery_dhl = fields.Boolean("DHL integration")
    module_delivery_fedex = fields.Boolean("Fedex integration")
    module_delivery_temando = fields.Boolean("Temando integration")
    module_delivery_ups = fields.Boolean("UPS integration")
    module_delivery_usps = fields.Boolean("USPS integration")
    # Warehouse and location usage_level
    warehouse_and_location_usage_level = fields.Selection([
        (0, 'Manage only 1 Warehouse with only 1 stock location'),
        (1, 'Manage only 1 Warehouse, composed by several stock locations'),
        (2, 'Manage several Warehouses, each one composed by several stock locations')
        ], "Warehouses and Locations usage level")
    group_stock_multi_locations = fields.Boolean('Manage several stock locations', implied_group='stock.group_stock_multi_locations')
    group_stock_multi_warehouses = fields.Boolean('Manage several warehouses', implied_group='stock.group_stock_multi_warehouses')
    module_quality = fields.Boolean(string="Quality", help="This module allows you to generate quality alerts and quality check")

    @api.onchange('warehouse_and_location_usage_level')
    def onchange_warehouse_and_location_usage_level(self):
        self.group_stock_multi_locations = self.warehouse_and_location_usage_level > 0
        self.group_stock_multi_warehouses = self.warehouse_and_location_usage_level > 1

    @api.onchange('group_stock_adv_location')
    def onchange_adv_location(self):
        if self.group_stock_adv_location and self.warehouse_and_location_usage_level == 0:
            self.warehouse_and_location_usage_level = 1

    @api.multi
    def set_group_stock_multi_locations(self):
        """ If we are not in multiple locations, we can deactivate the internal
        picking types of the warehouses, so they won't appear in the dashboard.
        Otherwise, activate them.
        """
        for config in self:
            if config.group_stock_multi_locations:
                active = True
                domain = []
            else:
                active = False
                domain = [('reception_steps', '=', 'one_step'), ('delivery_steps', '=', 'ship_only')]

            warehouses = self.env['stock.warehouse'].search(domain)
            warehouses.mapped('int_type_id').write({'active': active})

        return True
