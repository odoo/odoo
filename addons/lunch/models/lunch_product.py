# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools

from odoo.addons import decimal_precision as dp
from odoo.tools import formatLang


class LunchProductCategory(models.Model):
    """ Category of the product such as pizza, sandwich, pasta, chinese, burger... """
    _name = 'lunch.product.category'
    _description = 'Lunch Product Category'

    name = fields.Char('Product Category', required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env['res.company']._company_default_get())
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    topping_label_1 = fields.Char('Topping Label 1', required=True, default='Supplements')
    topping_label_2 = fields.Char('Topping Label 2', required=True, default='Beverages')
    topping_label_3 = fields.Char('Topping Label 3', required=True, default='Topping Label 3')
    topping_ids_1 = fields.One2many('lunch.topping', 'category_id', domain=[('topping_category', '=', 1)], ondelete='cascade')
    topping_ids_2 = fields.One2many('lunch.topping', 'category_id', domain=[('topping_category', '=', 2)], ondelete='cascade')
    topping_ids_3 = fields.One2many('lunch.topping', 'category_id', domain=[('topping_category', '=', 3)], ondelete='cascade')
    topping_quantity_1 = fields.Selection([
        ('0_more', 'None or More'),
        ('1_more', 'One or More'),
        ('1', 'Only One')], default='0_more', required=True)
    topping_quantity_2 = fields.Selection([
        ('0_more', 'None or More'),
        ('1_more', 'One or More'),
        ('1', 'Only One')], default='0_more', required=True)
    topping_quantity_3 = fields.Selection([
        ('0_more', 'None or More'),
        ('1_more', 'One or More'),
        ('1', 'Only One')], default='0_more', required=True)

    @api.model
    def create(self, vals):
        for topping in vals.get('topping_ids_2', []):
            topping[2].update({'topping_category': 2})
        for topping in vals.get('topping_ids_3', []):
            topping[2].update({'topping_category': 3})
        return super(LunchProductCategory, self).create(vals)

    def write(self, vals):
        for topping in vals.get('topping_ids_2', []):
            topping_values = topping[2]
            if topping_values:
                topping_values.update({'topping_category': 2})
        for topping in vals.get('topping_ids_3', []):
            topping_values = topping[2]
            if topping_values:
                topping_values.update({'topping_category': 3})
        return super(LunchProductCategory, self).write(vals)


class LunchTopping(models.Model):
    """"""
    _name = 'lunch.topping'
    _description = 'Lunch Toppings'

    name = fields.Char('Name', required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env['res.company']._company_default_get())
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    price = fields.Float('Price', digits=dp.get_precision('Account'), required=True)
    category_id = fields.Many2one('lunch.product.category')
    topping_category = fields.Integer('Topping Category', help="This field is a technical field", required=True, default=1)

    def name_get(self):
        currency_id = self.env.user.company_id.currency_id
        res = dict(super(LunchTopping, self).name_get())
        for topping in self:
            price = formatLang(self.env, topping.price, currency_obj=currency_id)
            res[topping.id] = '%s %s' % (topping.name, price)
        return list(res.items())


class LunchProduct(models.Model):
    """ Products available to order. A product is linked to a specific vendor. """
    _name = 'lunch.product'
    _description = 'Lunch Product'
    _order = 'name'

    name = fields.Char('Product Name', required=True)
    category_id = fields.Many2one('lunch.product.category', 'Product Category', required=True)
    description = fields.Text('Description')
    price = fields.Float('Price', digits=dp.get_precision('Account'), required=True)
    supplier_id = fields.Many2one('lunch.supplier', 'Vendor', required=True)
    active = fields.Boolean(default=True)

    company_id = fields.Many2one('res.company', default=lambda self: self.env['res.company']._company_default_get())
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

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

    new_until = fields.Date('New Until')
    favorite_user_ids = fields.Many2many('res.users', 'lunch_product_favorite_user_rel', 'product_id', 'user_id')


    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            tools.image_resize_images(values)
        return super(LunchProduct, self).create(vals_list)

    def write(self, values):
        tools.image_resize_images(values)
        return super(LunchProduct, self).write(values)
