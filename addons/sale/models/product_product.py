# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta, time
from odoo import api, fields, models
from odoo.tools.float_utils import float_round


class ProductProduct(models.Model):
    _inherit = 'product.product'

    sales_count = fields.Float(compute='_compute_sales_count', string='Sold')

    def _compute_sales_count(self):
        r = {}
        if not self.user_has_groups('sales_team.group_sale_salesman'):
            return r
        date_from = fields.Datetime.to_string(fields.datetime.combine(fields.datetime.now() - timedelta(days=365),
                                                                      time.min))

        done_states = self.env['sale.report']._get_done_states()

        domain = [
            ('state', 'in', done_states),
            ('product_id', 'in', self.ids),
            ('date', '>=', date_from),
        ]
        for group in self.env['sale.report'].read_group(domain, ['product_id', 'product_uom_qty'], ['product_id']):
            r[group['product_id'][0]] = group['product_uom_qty']
        for product in self:
            if not product.id:
                product.sales_count = 0.0
                continue
            product.sales_count = float_round(r.get(product.id, 0), precision_rounding=product.uom_id.rounding)
        return r

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

    def _get_combination_info_variant(self, add_qty=1, pricelist=False, parent_combination=False):
        """Return the variant info based on its combination.
        See `_get_combination_info` for more information.
        """
        self.ensure_one()
        return self.product_tmpl_id._get_combination_info(self.product_template_attribute_value_ids, self.id, add_qty, pricelist, parent_combination)


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

    attribute_value_id = fields.Many2one('product.attribute.value', string='Attribute Value')
    sale_order_line_id = fields.Many2one('sale.order.line', string='Sale order line')
    custom_value = fields.Char('Custom value')
