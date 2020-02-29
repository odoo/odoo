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
        self.sales_count = 0
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

    display_type = fields.Selection([
        ('radio', 'Radio'),
        ('select', 'Select'),
        ('color', 'Color')], default='radio', required=True, help="The display type used in the Product Configurator.")


class ProductAttributeValue(models.Model):
    _inherit = "product.attribute.value"

    is_custom = fields.Boolean('Is custom value', help="Allow users to input custom values for this attribute value")
    html_color = fields.Char(
        string='Color',
        help="Here you can set a specific HTML color index (e.g. #ff0000) to display the color if the attribute type is 'Color'.")
    display_type = fields.Selection(related='attribute_id.display_type', readonly=True)


class ProductTemplateAttributeValue(models.Model):
    _inherit = "product.template.attribute.value"

    html_color = fields.Char('HTML Color Index', related="product_attribute_value_id.html_color")
    is_custom = fields.Boolean('Is custom value', related="product_attribute_value_id.is_custom")
    display_type = fields.Selection(related='product_attribute_value_id.display_type', readonly=True)


class ProductAttributeCustomValue(models.Model):
    _name = "product.attribute.custom.value"
    _description = 'Product Attribute Custom Value'
    _order = 'custom_product_template_attribute_value_id, id'

    name = fields.Char("Name", compute='_compute_name')
    custom_product_template_attribute_value_id = fields.Many2one('product.template.attribute.value', string="Attribute Value", required=True, ondelete='restrict')
    sale_order_line_id = fields.Many2one('sale.order.line', string="Sales Order Line", required=True, ondelete='cascade')
    custom_value = fields.Char("Custom Value")

    @api.depends('custom_product_template_attribute_value_id.name', 'custom_value')
    def _compute_name(self):
        for record in self:
            name = (record.custom_value or '').strip()
            if record.custom_product_template_attribute_value_id.display_name:
                name = "%s: %s" % (record.custom_product_template_attribute_value_id.display_name, name)
            record.name = name

    _sql_constraints = [
        ('sol_custom_value_unique', 'unique(custom_product_template_attribute_value_id, sale_order_line_id)', "Only one Custom Value is allowed per Attribute Value per Sales Order Line.")
    ]
