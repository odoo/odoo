# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.modules.module import get_module_resource
from odoo.tools import formatLang


class LunchProductCategory(models.Model):
    """ Category of the product such as pizza, sandwich, pasta, chinese, burger... """
    _name = 'lunch.product.category'
    _inherit = 'image.mixin'
    _description = 'Lunch Product Category'

    @api.model
    def _default_image(self):
        image_path = get_module_resource('lunch', 'static/img', 'lunch.png')
        return base64.b64encode(open(image_path, 'rb').read())

    name = fields.Char('Product Category', required=True, translate=True)
    company_id = fields.Many2one('res.company')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    topping_label_1 = fields.Char('Extra 1 Label', required=True, default='Extras')
    topping_label_2 = fields.Char('Extra 2 Label', required=True, default='Beverages')
    topping_label_3 = fields.Char('Extra 3 Label', required=True, default='Extra Label 3')
    topping_ids_1 = fields.One2many('lunch.topping', 'category_id', domain=[('topping_category', '=', 1)])
    topping_ids_2 = fields.One2many('lunch.topping', 'category_id', domain=[('topping_category', '=', 2)])
    topping_ids_3 = fields.One2many('lunch.topping', 'category_id', domain=[('topping_category', '=', 3)])
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
    active = fields.Boolean(string='Active', default=True)
    image_1920 = fields.Image(default=_default_image)

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

    def toggle_active(self):
        """ Archiving related lunch product """
        res = super().toggle_active()
        Product = self.env['lunch.product'].with_context(active_test=False)
        all_products = Product.search([('category_id', 'in', self.ids)])
        for category in self:
            all_products.filtered(
                lambda p: p.category_id == category and p.active != category.active
            ).toggle_active()
        return res

class LunchTopping(models.Model):
    """"""
    _name = 'lunch.topping'
    _description = 'Lunch Extras'

    name = fields.Char('Name', required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    price = fields.Float('Price', digits='Account', required=True)
    category_id = fields.Many2one('lunch.product.category', ondelete='cascade')
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
    _inherit = 'image.mixin'
    _order = 'name'
    _check_company_auto = True

    name = fields.Char('Product Name', required=True, translate=True)
    category_id = fields.Many2one('lunch.product.category', 'Product Category', check_company=True, required=True)
    description = fields.Text('Description', translate=True)
    price = fields.Float('Price', digits='Account', required=True)
    supplier_id = fields.Many2one('lunch.supplier', 'Vendor', check_company=True, required=True)
    active = fields.Boolean(default=True)

    company_id = fields.Many2one('res.company', related='supplier_id.company_id', readonly=False, store=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    new_until = fields.Date('New Until')
    favorite_user_ids = fields.Many2many('res.users', 'lunch_product_favorite_user_rel', 'product_id', 'user_id', check_company=True)

    def toggle_active(self):
        if self.filtered(lambda product: not product.active and not product.category_id.active):
            raise UserError(_("The product category is archived. The user have to unarchive the category or change the category of the product."))
        return super().toggle_active()
