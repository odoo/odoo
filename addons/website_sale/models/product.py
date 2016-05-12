# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, tools, _


class ProductStyle(models.Model):
    _name = "product.style"

    name = fields.Char(string='Style Name', required=True)
    html_class = fields.Char(string='HTML Classes')


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    code = fields.Char(string='E-commerce Promotional Code')


class ProductPublicCategory(models.Model):
    _name = "product.public.category"
    _inherit = ["website.seo.metadata"]
    _description = "Website Product Category"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    parent_id = fields.Many2one('product.public.category', string='Parent Category', index=True)
    child_id = fields.One2many('product.public.category', 'parent_id', string='Children Categories')
    sequence = fields.Integer(help="Gives the sequence order when displaying a list of product categories.")
    # NOTE: there is no 'default image', because by default we don't show
    # thumbnails for categories. However if we have a thumbnail for at least one
    # category, then we display a default image on the other, so that the
    # buttons have consistent styling.
    # In this case, the default image is set by the js code.
    image = fields.Binary(attachment=True, help="This field holds the image used as image for the category, limited to 1024x1024px.")
    image_medium = fields.Binary(string='Medium-sized image', attachment=True,
                                 help="Medium-sized image of the category. It is automatically "
                                 "resized as a 128x128px image, with aspect ratio preserved. "
                                 "Use this field in form views or some kanban views.")
    image_small = fields.Binary(string='Small-sized image', attachment=True,
                                help="Small-sized image of the category. It is automatically "
                                "resized as a 64x64px image, with aspect ratio preserved. "
                                "Use this field anywhere a small image is required.")

    @api.model
    def create(self, vals):
        tools.image_resize_images(vals)
        return super(ProductPublicCategory, self).create(vals)

    @api.multi
    def write(self, vals):
        tools.image_resize_images(vals)
        return super(ProductPublicCategory, self).write(vals)

    @api.constrains('parent_id')
    def check_parent_id(self):
        if not self._check_recursion():
            raise ValueError(_('Error ! You cannot create recursive categories.'))

    @api.multi
    def name_get(self):
        res = []
        for category in self:
            names = [category.name]
            parent_category = category.parent_id
            while parent_category:
                names.append(parent_category.name)
                parent_category = parent_category.parent_id
            res.append((category.id, ' / '.join(reversed(names))))
        return res


class ProductTemplate(models.Model):
    _inherit = ["product.template", "website.seo.metadata", 'website.published.mixin', 'rating.mixin']
    _order = 'website_published desc, website_sequence desc, name'
    _name = 'product.template'
    _mail_post_access = 'read'

    website_message_ids = fields.One2many(
        'mail.message', 'res_id',
        domain=lambda self: ['&', ('model', '=', self._name), ('message_type', '=', 'comment')],
        string='Website Comments',
    )
    website_description = fields.Html('Description for the website', sanitize=False, translate=True)
    alternative_product_ids = fields.Many2many('product.template', 'product_alternative_rel', 'src_id', 'dest_id',
                                               string='Suggested Products', help='Appear on the product page')
    accessory_product_ids = fields.Many2many('product.product', 'product_accessory_rel', 'src_id', 'dest_id',
                                             string='Accessory Products', help='Appear on the shopping cart')
    website_size_x = fields.Integer('Size X', default=1)
    website_size_y = fields.Integer('Size Y', default=1)
    website_style_ids = fields.Many2many('product.style', string='Styles')
    website_sequence = fields.Integer('Website Sequence', help="Determine the display order in the Website E-commerce",
                                      default=lambda self: self._default_website_sequence())
    public_categ_ids = fields.Many2many('product.public.category', string='Website Product Category',
                                        help="Those categories are used to group similar products for e-commerce.")
    availability = fields.Selection([
        ('empty', 'Display Nothing'),
        ('in_stock', 'In Stock'),
        ('warning', 'Warning'),
    ], "Availability", default='empty', help="This field is used to display a availability banner with a message on the ecommerce")
    availability_warning = fields.Text("Availability Warning", translate=True)

    def _default_website_sequence(self):
        min_sequence = self.sudo().search([], order='website_sequence', limit=1).website_sequence
        return min_sequence and min_sequence - 1 or 10

    def set_sequence_top(self):
        self.website_sequence = self.sudo().search([], order='website_sequence desc', limit=1).website_sequence + 1

    def set_sequence_bottom(self):
        self.website_sequence = self.sudo().search([], order='website_sequence', limit=1).website_sequence - 1

    def set_sequence_up(self):
        previous_product_tmpl = self.sudo().search(
            [('website_sequence', '>', self.website_sequence), ('website_published', '=', self.website_published)],
            order='website_sequence', limit=1)
        if previous_product_tmpl:
            previous_product_tmpl.website_sequence, self.website_sequence = self.website_sequence, previous_product_tmpl.website_sequence
        else:
            self.set_sequence_top()

    def set_sequence_down(self):
        next_prodcut_tmpl = self.search([('website_sequence', '<', self.website_sequence), ('website_published', '=', self.website_published)], order='website_sequence desc', limit=1)
        if next_prodcut_tmpl:
            next_prodcut_tmpl.website_sequence, self.website_sequence = self.website_sequence, next_prodcut_tmpl.website_sequence
        else:
            return self.set_sequence_bottom()

    @api.multi
    def _website_url(self, field_name, arg):
        res = super(ProductTemplate, self)._website_url(field_name, arg)
        for product in self:
            res[product.id] = "/shop/product/%s" % (product.id,)
        return res

    @api.multi
    def display_price(self, pricelist, qty=1, public=False, **kw):
        self.ensure_one()
        return self.product_variant_ids and self.product_variant_ids[0].display_price(pricelist, qty=qty, public=public) or 0


class Product(models.Model):
    _inherit = "product.product"

    @api.multi
    def website_publish_button(self):
        self.ensure_one()
        return self.product_tmpl_id.website_publish_button()

    @api.multi
    def display_price(self, pricelist, qty=1, public=False, **kw):
        self.ensure_one()
        partner = self.env.user.partner_id
        context = {
            'pricelist': pricelist.id,
            'quantity': qty,
            'partner': partner
        }
        ret = self.env.user.has_group('sale.group_show_price_subtotal') and 'total_excluded' or 'total_included'
        taxes = partner.property_account_position_id.map_tax(self.taxes_id)
        return taxes.compute_all(public and self.lst_price or self.with_context(context).price, pricelist.currency_id, qty, product=self, partner=partner)[ret]


class ProductAttribute(models.Model):
    _inherit = "product.attribute"

    type = fields.Selection([('radio', 'Radio'), ('select', 'Select'), ('color', 'Color'), ('hidden', 'Hidden')], default='radio')


class ProductAttributeValue(models.Model):
    _inherit = "product.attribute.value"

    html_color = fields.Char(string='HTML Color Index', oldname='color', help="Here you can set a "
                             "specific HTML color index (e.g. #ff0000) to display the color on the website if the "
                             "attibute type is 'Color'.")
