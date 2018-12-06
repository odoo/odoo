# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP
from odoo.tools.float_utils import float_round
import json


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    service_type = fields.Selection([('manual', 'Manually set quantities on order')], string='Track Service',
        help="Manually set quantities on order: Invoice based on the manually entered quantity, without creating an analytic account.\n"
             "Timesheets on contract: Invoice based on the tracked hours on the related timesheet.\n"
             "Create a task and track hours: Create a task on the sales order validation and track the work hours.",
        default='manual', oldname='track_service')
    sale_line_warn = fields.Selection(WARNING_MESSAGE, 'Sales Order Line', help=WARNING_HELP, required=True, default="no-message")
    sale_line_warn_msg = fields.Text('Message for Sales Order Line')
    expense_policy = fields.Selection(
        [('no', 'No'), ('cost', 'At cost'), ('sales_price', 'Sales price')],
        string='Re-Invoice Expenses',
        default='no',
        help="Expenses and vendor bills can be re-invoiced to a customer."
             "With this option, a validated expense can be re-invoice to a customer at its cost or sales price.")
    visible_expense_policy = fields.Boolean("Re-Invoice Policy visible", compute='_compute_visible_expense_policy')
    sales_count = fields.Float(compute='_compute_sales_count', string='Sold')
    invoice_policy = fields.Selection([
        ('order', 'Ordered quantities'),
        ('delivery', 'Delivered quantities')], string='Invoicing Policy',
        help='Ordered Quantity: Invoice quantities ordered by the customer.\n'
             'Delivered Quantity: Invoice quantities delivered to the customer.',
        default='order')

    @api.multi
    @api.depends('name')
    def _compute_visible_expense_policy(self):
        visibility = self.user_has_groups('analytic.group_analytic_accounting')
        for product_template in self:
            product_template.visible_expense_policy = visibility

    @api.multi
    @api.depends('product_variant_ids.sales_count')
    def _compute_sales_count(self):
        for product in self:
            product.sales_count = float_round(sum([p.sales_count for p in product.with_context(active_test=False).product_variant_ids]), precision_rounding=product.uom_id.rounding)

    @api.multi
    def action_view_sales(self):
        action = self.env.ref('sale.report_all_channels_sales_action').read()[0]
        action['domain'] = [('product_tmpl_id', 'in', self.ids)]
        action['context'] = {
            'pivot_measures': ['product_uom_qty'],
            'active_id': self._context.get('active_id'),
            'active_model': 'sale.report',
            'search_default_Sales': 1,
            'time_ranges': {'field': 'date', 'range': 'last_365_days'}
        }
        return action

    def create_product_variant(self, product_template_attribute_value_ids):
        self.ensure_one()

        attribute_value_ids = \
            self.env['product.template.attribute.value'] \
                .browse(json.loads(product_template_attribute_value_ids)) \
                .mapped('product_attribute_value_id') \
                .filtered(lambda attribute_value_id: attribute_value_id.attribute_id.create_variant != 'no_variant')

        product_variant = self.env['product.product'].create({
            'product_tmpl_id': self.id,
            'attribute_value_ids': [(6, 0, attribute_value_ids.ids)]
        })

        return product_variant.id

    @api.onchange('type')
    def _onchange_type(self):
        """ Force values to stay consistent with integrity constraints """
        if self.type == 'consu':
            if not self.invoice_policy:
                self.invoice_policy = 'order'
            self.service_type = 'manual'

    @api.model
    def get_import_templates(self):
        res = super(ProductTemplate, self).get_import_templates()
        if self.env.context.get('sale_multi_pricelist_product_template'):
            sale_pricelist_setting = self.env['ir.config_parameter'].sudo().get_param('sale.sale_pricelist_setting')
            if sale_pricelist_setting == 'percentage':
                return [{
                    'label': _('Import Template for Products'),
                    'template': '/product/static/xls/product_template.xls'
                }, {
                    'label': _('Import Template for Products (with several prices)'),
                    'template': '/sale/static/xls/product_pricelist_several.xls'
                }]
        return res
