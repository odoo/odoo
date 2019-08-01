# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools

from odoo.tools import formatLang


class LunchProductCategory(models.Model):
    """ Category of the product such as pizza, sandwich, pasta, chinese, burger... """
    _name = 'lunch.product.category'
    _description = 'Lunch Product Category'

    name = fields.Char('Product Category', required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    topping_label_1 = fields.Char('Extra 1 Label', required=True, default='Extras')
    topping_label_2 = fields.Char('Extra 2 Label', required=True, default='Beverages')
    topping_label_3 = fields.Char('Extra 3 Label', required=True, default='Extra Label 3')
    topping_ids_1 = fields.One2many('lunch.topping', 'category_id', domain=[('topping_category', '=', 1)], ondelete='cascade')
    topping_ids_2 = fields.One2many('lunch.topping', 'category_id', domain=[('topping_category', '=', 2)], ondelete='cascade')
    topping_ids_3 = fields.One2many('lunch.topping', 'category_id', domain=[('topping_category', '=', 3)], ondelete='cascade')
    topping_quantity_1 = fields.Selection([
        ('0_more', 'None or More'),
        ('1_more', 'One or More'),
        ('1', 'Only One')], 'Extra 1 Quantity', default='0_more', required=True)
    topping_quantity_2 = fields.Selection([
        ('0_more', 'None or More'),
        ('1_more', 'One or More'),
        ('1', 'Only One')], 'Extra 2 Quantity', default='0_more', required=True)
    topping_quantity_3 = fields.Selection([
        ('0_more', 'None or More'),
        ('1_more', 'One or More'),
        ('1', 'Only One')], 'Extra 3 Quantity', default='0_more', required=True)
    product_count = fields.Integer(compute='_compute_product_count', help="The number of products related to this category")

    def _compute_product_count(self):
        product_data = self.env['lunch.product'].read_group([('category_id', 'in', self.ids)], ['category_id'], ['category_id'])
        data = {product['category_id'][0]: product['category_id_count'] for product in product_data}
        for category in self:
            category.product_count = data.get(category.id, 0)

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
    _description = 'Lunch Extras'

    name = fields.Char('Name', required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    price = fields.Float('Price', digits='Account', required=True)
    category_id = fields.Many2one('lunch.product.category')
    topping_category = fields.Integer('Topping Category', help="This field is a technical field", required=True, default=1)

    def name_get(self):
        currency_id = self.env.company.currency_id
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
    price = fields.Float('Price', digits='Account', required=True)
    supplier_id = fields.Many2one('lunch.supplier', 'Vendor', required=True)
    active = fields.Boolean(default=True)

    company_id = fields.Many2one('res.company', related='supplier_id.company_id', store=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    # image: all image fields are base64 encoded and PIL-supported
    image = fields.Binary(
        "Image",
        help="This field holds the image used as image for the product, limited to 1024x1024px.")
    image_128 = fields.Binary(
        "Medium-sized image",
        help="Medium-sized image of the product. It is automatically "
             "resized as a 128x128px image, with aspect ratio preserved, "
             "only when the image exceeds one of those sizes. Use this field in form views or some kanban views.")
    image_64 = fields.Binary(
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
