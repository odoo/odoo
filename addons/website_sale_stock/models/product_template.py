# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    inventory_availability = fields.Selection([
        ('always', 'Always'),
        ('never', 'Never'),
        ('threshold', 'Only below a threshold'),
    ], string='Inventory Availability', help='Adds an inventory availability status on the web product page.', default='never')
    available_threshold = fields.Float(string='Availability Threshold', default=5.0)
    allow_order = fields.Selection(selection=[
        ('always', 'Always'),
        ('enough', 'Only if enough inventory'),
    ], string='Allow to Order', default='enough')
    availability_information = fields.Selection([
        ('quantity', 'Quantity Available'),
        ('state', 'In Stock - Quantity Left - Out of stock'),
        ('custom', 'Custom Message'),
    ], string="Availability Information", default="state")
    custom_message = fields.Text(string='Custom Message', default='', translate=True)

    def _get_combination_info(self, combination=False, product_id=False, add_qty=1, pricelist=False, parent_combination=False, only_template=False):
        combination_info = super(ProductTemplate, self)._get_combination_info(
            combination=combination, product_id=product_id, add_qty=add_qty, pricelist=pricelist,
            parent_combination=parent_combination, only_template=only_template)

        if not self.env.context.get('website_sale_stock_get_quantity'):
            return combination_info

        if combination_info['product_id']:
            product = self.env['product.product'].sudo().browse(combination_info['product_id'])
            website = self.env['website'].get_current_website()
            product_with_context = product.with_context(warehouse=website.warehouse_id.id)
            qty_available = product_with_context.qty_available
            qty_forecasted = product_with_context.incoming_qty
            combination_info.update({
                'qty_available': qty_available,
                'qty_available_formatted': self.env['ir.qweb.field.float'].value_to_html(qty_available, {'decimal_precision': 'Product Unit of Measure'}),
                'qty_forecasted': qty_forecasted,
                'product_type': product.type,
                'inventory_availability': product.inventory_availability,
                'available_threshold': product.available_threshold,
                'allow_order': product.allow_order,
                'availability_information': product.availability_information,
                'custom_message': product.custom_message,
                'product_template': product.product_tmpl_id.id,
                'cart_qty': product.cart_qty,
                'uom_name': product.uom_id.name,
            })
        else:
            product_template = self.sudo()
            combination_info.update({
                'qty_available': 0,
                'product_type': product_template.type,
                'inventory_availability': product_template.inventory_availability,
                'available_threshold': product_template.available_threshold,
                'custom_message': product_template.custom_message,
                'product_template': product_template.id,
                'cart_qty': 0
            })
        # To remove, combination_info dict debug print
        for key in combination_info:
            print(f"\t'{key}': {combination_info[key]}")
        return combination_info
