# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    available_threshold = fields.Float(string='Availability Threshold', default=5.0)
    allow_order = fields.Selection(selection=[
        ('always', 'Always'),
        ('enough', 'Only if enough inventory'),
    ], string='Allow Orders', default='enough')
    in_stock = fields.Html(string="In Stock", translate=True, default="""<i class="text-success fa fa-check"/> <span style="color:green">In stock</span>""", sanitize_tags=False)
    below_threshold = fields.Html(string="Below Threshold", translate=True, default="""<i class="text-warning fa fa-exclamation-triangle"/> <span style="color:orange">Only {qty_available} {uom_name} left</span>""")
    no_stock = fields.Html(string="No Stock", translate=True, default="""<i class="text-danger fa fa-remove"/> <span style="color:red">Out Of Stock</span>""")

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
                'available_threshold': product.available_threshold,
                'allow_order': product.allow_order,
                'product_template': product.product_tmpl_id.id,
                'cart_qty': product.cart_qty,
                'uom_name': product.uom_id.name,
                'in_stock': product.in_stock,
                'below_threshold': product.below_threshold,
                'no_stock': product.no_stock,
            })
        else:
            product_template = self.sudo()
            combination_info.update({
                'qty_available': 0,
                'product_type': product_template.type,
                'available_threshold': product_template.available_threshold,
                'product_template': product_template.id,
                'cart_qty': 0
            })
        return combination_info
