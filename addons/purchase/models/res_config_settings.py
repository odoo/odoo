# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

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
    module_purchase_requisition = fields.Boolean("Purchase Agreements")
    group_warning_purchase = fields.Boolean("Warnings", implied_group='purchase.group_warning_purchase')
    module_stock_dropshipping = fields.Boolean("Dropshipping")
    group_manage_vendor_price = fields.Boolean("Vendor Pricelists",
        implied_group="purchase.group_manage_vendor_price")
    module_account_3way_match = fields.Boolean("3-way matching: purchases, receptions and bills")
    is_installed_sale = fields.Boolean(string="Is the Sale Module Installed")
    group_analytic_account_for_purchases = fields.Boolean('Analytic accounting for purchases',
        implied_group='purchase.group_analytic_accounting')

    @api.multi
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            is_installed_sale=self.env['ir.module.module'].search([('name', '=', 'sale'), ('state', '=', 'installed')]).id
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.po_lock = 'lock' if self.lock_confirmed_po else 'edit'
        self.po_double_validation = 'two_step' if self.po_order_approval else 'one_step'


