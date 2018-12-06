# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, tools, _

from odoo.addons import decimal_precision as dp


class LunchProductCategory(models.Model):
    """ Category of the product such as pizza, sandwich, pasta, chinese, burger... """
    _name = 'lunch.product.category'
    _description = 'Lunch Product Category'

    name = fields.Char('Product Category', required=True)
    topping_ids = fields.One2many('lunch.topping', 'category_id')


class LunchToppingType(models.Model):
    """"""
    _name = 'lunch.topping.type'
    _description = 'Lunch Topping Type'

    name = fields.Char('Name', required=True)


class LunchTopping(models.Model):
    """"""
    _name = 'lunch.topping'
    _description = 'Lunch Toppings'

    name = fields.Char('Name', required=True)
    price = fields.Float('Price', digits=dp.get_precision('Account'), required=True)
    category_id = fields.Many2one('lunch.product.category')
    type_id = fields.Many2one('lunch.topping.type')

    def name_get(self):
        currency_id = self.env.user.company_id.currency_id
        res = dict(super(LunchTopping, self).name_get())
        for topping in self:
            if currency_id.position == 'before':
                price = '%s %s' % (currency_id.symbol, topping.price)
            else:
                price = '%s %s' % (topping.price, currency_id.symbol)
            res[topping.id] = '%s %s' % (topping.name, price)
        return list(res.items())


class LunchProduct(models.Model):
    """ Products available to order. A product is linked to a specific vendor. """
    _name = 'lunch.product'
    _description = 'Lunch Product'

    name = fields.Char('Name', required=True)
    category_id = fields.Many2one('lunch.product.category', 'Product Category', required=True)
    description = fields.Text('Description')
    price = fields.Float('Price', digits=dp.get_precision('Account'), required=True)
    supplier_id = fields.Many2one('lunch.supplier', 'Vendor', required=True)
    active = fields.Boolean(default=True)

    # image: all image fields are base64 encoded and PIL-supported
    image = fields.Binary(
        "Image",
        help="This field holds the image used as image for the product, limited to 1024x1024px.")
    image_medium = fields.Binary(
        "Medium-sized image",
        help="Medium-sized image of the product. It is automatically "
             "resized as a 128x128px image, with aspect ratio preserved, "
             "only when the image exceeds one of those sizes. Use this field in form views or some kanban views.")
    image_small = fields.Binary(
        "Small-sized image",
        help="Small-sized image of the product. It is automatically "
             "resized as a 64x64px image, with aspect ratio preserved. "
             "Use this field anywhere a small image is required.")

    already_ordered = fields.Boolean('Has Already Been Ordered', compute='_compute_already_ordered')

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        res = super(LunchProduct, self).search_read(domain, fields, offset, limit, order)

        if not order and 'already_ordered' in fields:
            res = sorted(res, key=lambda x: x['already_ordered'], reverse=True)

        return res

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            tools.image_resize_images(values)
        return super(LunchProduct, self).create(vals_list)

    def write(self, values):
        tools.image_resize_images(values)
        return super(LunchProduct, self).write(values)

    def _compute_already_ordered(self):
        last_ordered = fields.Date.today() - relativedelta(weeks=2)
        for product in self:
            product.already_ordered = bool(self.env['lunch.order.line'].search_count(
                [('product_id', '=', product.id), ('date', '>=', last_ordered), ('user_id', '=', self.env.user.id)]))
