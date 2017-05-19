# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PurchaseConfigSettings(models.TransientModel):
    _name = 'purchase.config.settings'
    _inherit = 'res.config.settings'

    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env.user.company_id)
    lock_confirmed_po = fields.Boolean("Lock Confirmed Orders", default=lambda self: self.env.user.company_id.po_lock == 'lock')
    po_lock = fields.Selection(related='company_id.po_lock', string="Purchase Order Modification *")
    po_order_approval = fields.Boolean("Order Approval", default=lambda self: self.env.user.company_id.po_double_validation == 'two_step')
    po_double_validation = fields.Selection(related='company_id.po_double_validation', string="Levels of Approvals *")
    po_double_validation_amount = fields.Monetary(related='company_id.po_double_validation_amount', string="Minimum Amount", currency_field='company_currency_id')
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True,
        help='Utility field to express amount currency')
    default_purchase_method = fields.Selection([
        ('purchase', 'Ordered quantities'),
        ('receive', 'Delivered quantities'),
        ], string="Bill Control", default_model="product.template",
        help="This default value is applied to any new product created. "
        "This can be changed in the product detail form.", default="receive")
    group_product_variant = fields.Boolean("Attributes & Variants",
        implied_group='product.group_product_variant')
    group_uom = fields.Boolean("Units of Measure",
        implied_group='product.group_uom')
    module_purchase_requisition = fields.Boolean("Purchase Agreements")
    group_warning_purchase = fields.Boolean("Warnings", implied_group='purchase.group_warning_purchase')
    module_stock_dropshipping = fields.Boolean("Dropshipping")
    group_manage_vendor_price = fields.Boolean("Vendor Pricelists",
        implied_group="purchase.group_manage_vendor_price")
    module_sale = fields.Boolean("Sales")
    module_mrp = fields.Boolean("Manufacturing")
    is_installed_sale = fields.Boolean()

    @api.multi
    def get_default_is_installed_sale(self, fields):
        return {
            'is_installed_sale': self.env['ir.module.module'].search([('name', '=', 'sale'), ('state', '=', 'installed')]).id
        }

    @api.multi
    def set_lock_confirmed_po(self):
        self.po_lock = 'lock' if self.lock_confirmed_po else 'edit'

    @api.multi
    def set_po_order_approval(self):
        self.po_double_validation = 'two_step' if self.po_order_approval else 'one_step'


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'
    group_analytic_account_for_purchases = fields.Boolean('Analytic accounting for purchases',
        implied_group='purchase.group_analytic_accounting')
