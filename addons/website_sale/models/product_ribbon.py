# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductRibbon(models.Model):
    _name = 'product.ribbon'
    _description = "Product ribbon"

    name = fields.Char(string="Ribbon Name", required=True, translate=True, size=20)
    bg_color = fields.Char(string="Background Color", required=True, default='#000000')
    text_color = fields.Char(string="Text Color", required=True, default='#FFFFFF')
    position = fields.Selection(
        string='Position',
        selection=[('left', "Left"), ('right', "Right")],
        required=True,
        default='left',
    )
    style = fields.Selection(
        string="Style",
        selection=[('ribbon', "Ribbon"), ('tag', "Badge")],
        required=True,
        default='ribbon',
    )
    assign = fields.Selection(
        string="Assign",
        selection=[
            ('manual', "Manually"),
            ('sale', "Sale"),
            ('new', "New"),
        ],
        required=True,
        default='manual'
    )
    new_period = fields.Integer(default=30)

    def _get_position_class(self):
        return f'o_{self.style or "ribbon"}_{self.position or "left"}'

    def _get_ribbon(self, product, variant, product_prices):
        manually_set_ribbon = (
            (product and product.website_ribbon_id)
            or (variant and variant.variant_ribbon_id)
        )
        if manually_set_ribbon:
            return manually_set_ribbon

        if product_prices:
            sale_product_grid = 'base_price' in product_prices
            sale_product_images = product_prices.get('list_price', 0) != product_prices.get('price', 0)
            if sale_product_grid or sale_product_images:
                return self.sudo().search([('assign', '=', 'sale')], limit=1)

        new_ribbon = self.sudo().search(
            [
                ('assign', '=', 'new'),
                ('new_period', '>=', (fields.Datetime.today() - product.publish_date).days),
            ],
            order="new_period",
            limit=1,
        )
        if new_ribbon:
                return new_ribbon
        return self

