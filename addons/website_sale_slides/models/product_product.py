from odoo import _, api, fields, models


class Product(models.Model):
    _inherit = "product.product"

    channel_ids = fields.One2many('slide.channel', 'product_id', string='Courses')
    is_slide_channel = fields.Boolean(compute="_compute_is_slide_channel")

    def _compute_is_slide_channel(self):
        has_slide_channel_per_product = {
            product.id: bool(count)
            for product, count in self.env['slide.channel']._read_group(
                domain=[
                    ('product_id', '!=', False),
                ],
                groupby=['product_id'],
                aggregates=['__count'],
            )
        }
        for product in self:
            product.is_slide_channel = has_slide_channel_per_product.get(product.id, False)

    def get_product_multiline_description_sale(self):
        payment_channels = self.channel_ids.filtered(lambda course: course.enroll == 'payment')

        if not payment_channels:
            return super(Product, self).get_product_multiline_description_sale()

        new_line = '' if len(payment_channels) == 1 else '\n'
        return _('Access to: %s%s', new_line, '\n'.join(payment_channels.mapped('name')))

    def _is_allow_zero_price(self):
        return super()._is_allow_zero_price() or self.is_slide_channel
