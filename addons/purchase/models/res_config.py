# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PurchaseConfigSettings(models.TransientModel):
    _name = 'purchase.config.settings'
    _inherit = 'res.config.settings'

    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env.user.company_id)
    po_lead = fields.Float(related='company_id.po_lead', string="Purchase Lead Time *")
    po_lock = fields.Selection(related='company_id.po_lock', string="Purchase Order Modification *")
    po_double_validation = fields.Selection(related='company_id.po_double_validation', string="Levels of Approvals *")
    po_double_validation_amount = fields.Monetary(related='company_id.po_double_validation_amount', string="Double validation amount *", currency_field='company_currency_id')
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True,
        help='Utility field to express amount currency')
    group_product_variant = fields.Selection([
        (0, "No variants on products"),
        (1, 'Products can have several attributes, defining variants (Example: size, color,...)')
        ], "Product Variants",
        help='Work with product variant allows you to define some variant of the same products, an ease the product management in the ecommerce for example',
        implied_group='product.group_product_variant')
    group_uom = fields.Selection([
        (0, 'Products have only one unit of measure (easier)'),
        (1, 'Some products may be sold/puchased in different units of measure (advanced)')
        ], "Units of Measure",
        implied_group='product.group_uom',
        help="""Allows you to select and maintain different units of measure for products.""")
    group_costing_method = fields.Selection([
        (0, 'Set a fixed cost price on each product'),
        (1, "Use a 'Fixed', 'Real' or 'Average' price costing method")
        ], "Costing Methods",
        implied_group='stock_account.group_inventory_valuation',
        help="""Allows you to compute product cost price based on average cost.""")
    module_purchase_requisition = fields.Selection([
        (0, 'Purchase propositions trigger draft purchase orders to a single supplier'),
        (1, 'Allow using call for tenders to get quotes from multiple suppliers (advanced)')
        ], "Calls for Tenders",
        help="Calls for tenders are used when you want to generate requests for quotations to several vendors for a given set of products.\n"
             "You can configure per product if you directly do a Request for Quotation "
             "to one vendor or if you want a Call for Tenders to compare offers from several vendors.")
    group_warning_purchase = fields.Selection([
        (0, 'All the products and the customers can be used in purchase orders'),
        (1, 'An informative or blocking warning can be set on a product or a customer')
        ], "Warning", implied_group='purchase.group_warning_purchase')
    module_stock_dropshipping = fields.Selection([
        (0, 'Suppliers always deliver to your warehouse(s)'),
        (1, "Allow suppliers to deliver directly to your customers")
        ], "Dropshipping",
        help='\nCreates the dropship Route and add more complex tests\n'
             '-This installs the module stock_dropshipping.')
    group_manage_vendor_price = fields.Selection([
        (0, 'Manage vendor price on the product form'),
        (1, 'Allow using and importing vendor pricelists')
        ], "Vendor Price",
        implied_group="purchase.group_manage_vendor_price")


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'
    group_analytic_account_for_purchases = fields.Boolean('Analytic accounting for purchases',
        implied_group='purchase.group_analytic_accounting',
        help="Allows you to specify an analytic account on purchase order lines.")
