# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models, _
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP
from odoo.tools.float_utils import float_round


class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = 'product.template'

    property_account_creditor_price_difference = fields.Many2one(
        'account.account', string="Price Difference Account", company_dependent=True,
        help="This account is used in automated inventory valuation to "\
             "record the price difference between a purchase order and its related vendor bill when validating this vendor bill.")
    purchased_product_qty = fields.Float(compute='_compute_purchased_product_qty', string='Purchased')
    purchase_method = fields.Selection([
        ('purchase', 'On ordered quantities'),
        ('receive', 'On received quantities'),
    ], string="Control Policy", help="On ordered quantities: Control bills based on ordered quantities.\n"
        "On received quantities: Control bills based on received quantities.", default="receive")
    purchase_line_warn = fields.Selection(WARNING_MESSAGE, 'Purchase Order Line', help=WARNING_HELP, required=True, default="no-message")
    purchase_line_warn_msg = fields.Text('Message for Purchase Order Line')

    @api.multi
    def _compute_purchased_product_qty(self):
        for template in self:
            template.purchased_product_qty = float_round(sum([p.purchased_product_qty for p in template.product_variant_ids]), precision_rounding=template.uom_id.rounding)

    @api.model
    def get_import_templates(self):
        res = super(ProductTemplate, self).get_import_templates()
        if self.env.context.get('purchase_product_template'):
            return [{
                'label': _('Import Template for Products'),
                'template': '/purchase/static/xls/product_purchase.xls'
            }]
        return res

    @api.multi
    def action_view_po(self):
        action = self.env.ref('purchase.action_purchase_order_report_all').read()[0]
        action['domain'] = ['&', ('state', 'in', ['purchase', 'done']), ('product_tmpl_id', 'in', self.ids)]
        action['context'] = {
            'search_default_last_year_purchase': 1,
            'search_default_status': 1, 'search_default_order_month': 1,
            'graph_measure': 'unit_quantity'
        }
        return action


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = 'product.product'

    purchased_product_qty = fields.Float(compute='_compute_purchased_product_qty', string='Purchased')

    @api.multi
    def _compute_purchased_product_qty(self):
        date_from = fields.Datetime.to_string(fields.datetime.now() - timedelta(days=365))
        domain = [
            ('state', 'in', ['purchase', 'done']),
            ('product_id', 'in', self.mapped('id')),
            ('date_order', '>', date_from)
        ]
        PurchaseOrderLines = self.env['purchase.order.line'].search(domain)
        order_lines = self.env['purchase.order.line'].read_group(domain, ['product_id', 'product_uom_qty'], ['product_id'])
        purchased_data = dict([(data['product_id'][0], data['product_uom_qty']) for data in order_lines])
        for product in self:
            product.purchased_product_qty = float_round(purchased_data.get(product.id, 0), precision_rounding=product.uom_id.rounding)

    @api.multi
    def action_view_po(self):
        action = self.env.ref('purchase.action_purchase_order_report_all').read()[0]
        action['domain'] = ['&', ('state', 'in', ['purchase', 'done']), ('product_id', 'in', self.ids)]
        action['context'] = {
            'search_default_last_year_purchase': 1,
            'search_default_status': 1, 'search_default_order_month': 1,
            'graph_measure': 'unit_quantity'
        }
        return action


class ProductCategory(models.Model):
    _inherit = "product.category"

    property_account_creditor_price_difference_categ = fields.Many2one(
        'account.account', string="Price Difference Account",
        company_dependent=True,
        help="This account will be used to value price difference between purchase price and accounting cost.")


class SupplierInfo(models.Model):
    _inherit = "product.supplierinfo"

    @api.onchange('name')
    def _onchange_partner_id(self):
        self.currency_id = self.name.property_purchase_currency_id or self.env.user.company_id.currency_id
