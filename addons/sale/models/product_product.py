# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta, time
from odoo import api, fields, models
from odoo.tools.float_utils import float_round


class ProductTemplate(models.Model):
    _inherit = "product.template"

    optional_product_ids = fields.Many2many(
        'product.template', 'product_optional_rel', 'src_id', 'dest_id',
        string='Optional Products', help="Optional Products are suggested "
        "whenever the customer hits *Add to Cart* (cross-sell strategy, "
        "e.g. for computers: warranty, software, etc.).")


class ProductProduct(models.Model):
    _inherit = 'product.product'

    sales_count = fields.Float(compute='_compute_sales_count', string='Sold')

    @api.multi
    def _compute_sales_count(self):
        r = {}
        if not self.user_has_groups('sales_team.group_sale_salesman'):
            return r
        date_from = fields.Datetime.to_string(fields.datetime.combine(fields.datetime.now() - timedelta(days=365),
                                                                      time.min))
        date_to = fields.Datetime.to_string(fields.datetime.combine(fields.datetime.today(), time.min))
        domain = [
            ('state', 'in', ['sale', 'done', 'paid']),
            ('product_id', 'in', self.ids),
            ('date', '>=', date_from),
            ('date', '<', date_to)
        ]
        for group in self.env['sale.report'].read_group(domain, ['product_id', 'product_uom_qty'], ['product_id']):
            r[group['product_id'][0]] = group['product_uom_qty']
        for product in self:
            product.sales_count = float_round(r.get(product.id, 0), precision_rounding=product.uom_id.rounding)
        return r

    @api.multi
    def action_view_sales(self):
        action = self.env.ref('sale.report_all_channels_sales_action').read()[0]
        action['domain'] = [('product_id', 'in', self.ids)]
        action['context'] = {
            'pivot_measures': ['product_uom_qty'],
            'active_id': self._context.get('active_id'),
            'search_default_Sales': 1,
            'active_model': 'sale.report',
            'time_ranges': {'field': 'date', 'range': 'last_365_days'},
        }
        return action

    def _get_invoice_policy(self):
        return self.invoice_policy


class ProductAttribute(models.Model):
    _inherit = "product.attribute"

    # YTI FIX ME: PLEASE RENAME ME INTO attribute_type
    type = fields.Selection([
        ('radio', 'Radio'),
        ('select', 'Select'),
        ('color', 'Color')], default='radio', required=True)


class ProductAttributeValue(models.Model):
    _inherit = "product.attribute.value"

    is_custom = fields.Boolean('Is custom value', help="Allow users to input custom values for this attribute value")
    html_color = fields.Char(
        string='HTML Color Index', oldname='color',
        help="""Here you can set a
        specific HTML color index (e.g. #ff0000) to display the color if the
        attribute type is 'Color'.""")


class ProductTemplateAttributeValue(models.Model):
    _inherit = "product.template.attribute.value"

    html_color = fields.Char('HTML Color Index', related="product_attribute_value_id.html_color")
    is_custom = fields.Boolean('Is custom value', related="product_attribute_value_id.is_custom")


class ProductAttributeCustomValue(models.Model):
    _name = "product.attribute.custom.value"
    _rec_name = 'custom_value'
    _description = 'Product Attribute Custom Value'

    attribute_value_id = fields.Many2one('product.attribute.value', string='Attribute')
    sale_order_line_id = fields.Many2one('sale.order.line', string='Sale order line')
    custom_value = fields.Char('Custom value')
