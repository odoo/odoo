# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, tools, _
import odoo.addons.decimal_precision as dp
from odoo.tools.translate import html_translate


class ProductStyle(models.Model):
    _name = "product.style"

    name = fields.Char(string='Style Name', required=True)
    html_class = fields.Char(string='HTML Classes')


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    def _default_website(self):
        return self.env['website'].search([], limit=1)

    website_id = fields.Many2one('website', string="website", default=_default_website)
    code = fields.Char(string='E-commerce Promotional Code')
    selectable = fields.Boolean(help="Allow the end user to choose this price list")

    def clear_cache(self):
        # website._get_pl() is cached to avoid to recompute at each request the
        # list of available pricelists. So, we need to invalidate the cache when
        # we change the config of website price list to force to recompute.
        website = self.env['website']
        website._get_pl_partner_order.clear_cache(website)

    @api.model
    def create(self, data):
        res = super(ProductPricelist, self).create(data)
        self.clear_cache()
        return res

    @api.multi
    def write(self, data):
        res = super(ProductPricelist, self).write(data)
        self.clear_cache()
        return res

    @api.multi
    def unlink(self):
        res = super(ProductPricelist, self).unlink()
        self.clear_cache()
        return res


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
    website_description = fields.Html('Description for the website', sanitize_attributes=False, translate=html_translate)
    alternative_product_ids = fields.Many2many('product.template', 'product_alternative_rel', 'src_id', 'dest_id',
                                               string='Alternative Products', help='Suggest more expensive alternatives to '
                                               'your customers (upsell strategy). Those products show up on the product page.')
    accessory_product_ids = fields.Many2many('product.product', 'product_accessory_rel', 'src_id', 'dest_id',
                                             string='Accessory Products', help='Accessories show up when the customer reviews the '
                                             'cart before paying (cross-sell strategy, e.g. for computers: mouse, keyboard, etc.). '
                                             'An algorithm figures out a list of accessories based on all the products added to cart.')
    website_size_x = fields.Integer('Size X', default=1)
    website_size_y = fields.Integer('Size Y', default=1)
    website_style_ids = fields.Many2many('product.style', string='Styles')
    website_sequence = fields.Integer('Website Sequence', help="Determine the display order in the Website E-commerce",
                                      default=lambda self: self._default_website_sequence())
    public_categ_ids = fields.Many2many('product.public.category', string='Website Product Category',
                                        help="Categories can be published on the Shop page (online catalog grid) to help "
                                        "customers find all the items within a category. To publish them, go to the Shop page, "
                                        "hit Customize and turn *Product Categories* on. A product can belong to several categories.")
    availability = fields.Selection([
        ('empty', 'Display Nothing'),
        ('in_stock', 'In Stock'),
        ('warning', 'Warning'),
    ], "Availability", default='empty', help="Adds an availability status on the web product page.")
    availability_warning = fields.Text("Availability Warning", translate=True)
    product_image_ids = fields.One2many('product.image', 'product_tmpl_id', string='Images')

    website_price = fields.Float('Website price', compute='_website_price', digits=dp.get_precision('Product Price'))
    website_public_price = fields.Float('Website public price', compute='_website_price', digits=dp.get_precision('Product Price'))

    def _website_price(self):
        self.mapped('product_variant_id')

        for p in self:
            p.website_price = p.product_variant_id.website_price
            p.website_public_price = p.product_variant_id.website_public_price

    def _default_website_sequence(self):
        self._cr.execute("SELECT MIN(website_sequence) FROM %s" % self._table)
        min_sequence = self._cr.fetchone()[0]
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
    def _compute_website_url(self):
        super(ProductTemplate, self)._compute_website_url()
        for product in self:
            product.website_url = "/shop/product/%s" % (product.id,)


class Product(models.Model):
    _inherit = "product.product"

    website_price = fields.Float('Website price', compute='_website_price', digits=dp.get_precision('Product Price'))
    website_public_price = fields.Float('Website public price', compute='_website_price', digits=dp.get_precision('Product Price'))

    def _website_price(self):
        qty = self._context.get('quantity', 1.0)
        partner = self.env.user.partner_id
        pricelist = self.env['website'].get_current_website().get_current_pricelist()

        context = dict(self._context, pricelist=pricelist.id, partner=partner)
        self2 = self.with_context(context) if self._context != context else self

        ret = self.env.user.has_group('sale.group_show_price_subtotal') and 'total_excluded' or 'total_included'

        for p, p2 in zip(self, self2):
            taxes = partner.property_account_position_id.map_tax(p.taxes_id)
            p.website_price = taxes.compute_all(p2.price, pricelist.currency_id, quantity=qty, product=p2, partner=partner)[ret]
            p.website_public_price = taxes.compute_all(p2.lst_price, quantity=qty, product=p2, partner=partner)[ret]

    @api.multi
    def website_publish_button(self):
        self.ensure_one()
        return self.product_tmpl_id.website_publish_button()

class ProductAttribute(models.Model):
    _inherit = "product.attribute"

    type = fields.Selection([('radio', 'Radio'), ('select', 'Select'), ('color', 'Color'), ('hidden', 'Hidden')], default='radio')


class ProductAttributeValue(models.Model):
    _inherit = "product.attribute.value"

    html_color = fields.Char(string='HTML Color Index', oldname='color', help="Here you can set a "
                             "specific HTML color index (e.g. #ff0000) to display the color on the website if the "
                             "attibute type is 'Color'.")


class ProductImage(models.Model):
    _name = 'product.image'

    name = fields.Char('Name')
    image = fields.Binary('Image', attachment=True)
    product_tmpl_id = fields.Many2one('product.template', 'Related Product', copy=True)
