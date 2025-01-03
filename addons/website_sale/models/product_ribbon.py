# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models

from odoo.exceptions import ValidationError


class ProductRibbon(models.Model):
    _name = 'product.ribbon'
    _description = "Product ribbon"
    _order = "sequence"

    name = fields.Char(string="Ribbon Name", required=True, translate=True, size=20)
    sequence = fields.Integer(default=10)
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

    def _get_automatic_assigns(self):
        return ['new', 'sale']

    @api.constrains('assign')
    def _check_assign(self):
        for record in self:
            if record.assign in self._get_automatic_assigns():
                existing_ribbons = self.search([
                    ('id', '!=', record.id),
                    ('assign', '=', record.assign)
                ], limit=1)
                if existing_ribbons:
                    raise ValidationError(
                        _(
                            "Only one record with the assign %s is allowed." ,
                            dict(self._fields['assign'].selection).get(record.assign)
                        )
                    )

    def _get_position_class(self):
        if not self:
            return 'd-none'
        return f'o_{self.style or "ribbon"}_{self.position or "left"}'

    def _get_ribbon(self, product, variant, product_prices):
        manually_set_ribbon = (
            (product and product.website_ribbon_id)
            or (variant and variant.variant_ribbon_id)
        )
        if manually_set_ribbon:
            return manually_set_ribbon

        auto_assign_ribbons = self.sudo().search([('assign', '!=', 'manual')])
        for ribbon in auto_assign_ribbons:
            if ribbon._match_assign(product, product_prices):
                return ribbon
        return self

    def _match_assign(self, product, product_prices):
        is_sale_assign = (
            self.assign == 'sale'
            and product_prices
            and (
                'base_price' in product_prices
                or product_prices.get('list_price', 0) != product_prices.get('price', 0)
            )
        )

        is_new_assign = (
            self.assign == 'new'
            and self.new_period >= (fields.Datetime.today() - product.publish_date).days
        )

        return is_sale_assign or is_new_assign
