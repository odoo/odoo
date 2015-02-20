# -*- coding: utf-8 -*-
from openerp import api, fields, models, tools


class ProductStyle(models.Model):
    _name = "product.style"

    name = fields.Char('Style Name', required=True)
    html_class = fields.Char('HTML Classes')


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    code = fields.Char('Promotional Code')


class ProductPublicCategory(models.Model):
    _name = "product.public.category"
    _inherit = ["website.seo.metadata"]
    _description = "Public Category"
    _order = "sequence, name"

    @api.model
    def _check_recursion(self, parent=None):
        return super(ProductPublicCategory, self)._check_recursion(parent=parent)

    _constraints = [
        (_check_recursion, 'Error ! You cannot create recursive categories.', ['parent_id'])
    ]

    @api.multi
    def name_get(self):
        res = []
        for cat in self:
            names = [cat.name]
            pcat = cat.parent_id
            while pcat:
                names.append(pcat.name)
                pcat = pcat.parent_id
            res.append((cat.id, ' / '.join(reversed(names))))
        return res

    name = fields.Char(required=True, translate=True)
    complete_name = fields.Char(compute="_compute_name", string='Name')

    @api.multi
    def _compute_name(self):
        for record in self:
            record.complete_name = record.name_get()[0][1]

    parent_id = fields.Many2one('product.public.category', string='Parent Category', index=True)
    child_id = fields.One2many('product.public.category', 'parent_id', string='Children Categories')
    sequence = fields.Integer(help="Gives the sequence order when displaying a list of product categories.")

    # NOTE: there is no 'default image', because by default we don't show thumbnails for categories. However if we have a thumbnail
    # for at least one category, then we display a default image on the other, so that the buttons have consistent styling.
    # In this case, the default image is set by the js code.
    # NOTE2: image: all image fields are base64 encoded and PIL-supported
    image = fields.Binary(help="This field holds the image used as image for the category, limited to 1024x1024px.")
    image_medium = fields.Binary(string='Medium-sized image', compute="_compute_image",
                                 inverse="_inverse_image_medium", store=True,
                                 help="Medium-sized image of the category. It is automatically"
                                 "resized as a 128x128px image, with aspect ratio preserved."
                                 "Use this field in form views or some kanban views.")
    image_small = fields.Binary(string='Small-sized image', compute="_compute_image",
                                inverse="_inverse_image_small", store=True,
                                help="Small-sized image of the category. It is automatically"
                                "resized as a 64x64px image, with aspect ratio preserved."
                                "Use this field anywhere a small image is required.")

    @api.multi
    @api.depends('image')
    def _compute_image(self):
        for record in self:
            if record.image:
                record.image_medium = tools.image_resize_image_medium(record.image)
                record.image_small = tools.image_resize_image_small(record.image)

    def _inverse_image_medium(self):
        self.image = tools.image_resize_image_big(self.image_medium)

    def _inverse_image_small(self):
        self.image = tools.image_resize_image_big(self.image_small)

class ProductTemplate(models.Model):
    _inherit = ["product.template", "website.seo.metadata", 'website.published.mixin']
    _order = 'website_published desc, website_sequence desc, name'
    _name = 'product.template'
    _mail_post_access = 'read'

    @api.multi
    def _website_url(self, field_name, arg):
        res = super(ProductTemplate, self)._website_url(field_name, arg)
        for product in self:
            res[product.id] = "/shop/product/%s" % (product.id,)
        return res

    # TODO FIXME tde: when website_mail/mail_thread.py inheritance work -> this field won't be necessary
    website_message_ids = fields.One2many(
        'mail.message', 'res_id',
        domain=lambda self: [
            '&', ('model', '=', self._name), ('type', '=', 'comment')
        ],
        string='Website Comments'
    )
    website_description = fields.Html('Description for the website', translate=True)
    alternative_product_ids = fields.Many2many('product.template', 'product_alternative_rel', 'src_id', 'dest_id', string='Alternative Products', help='Appear on the product page')
    accessory_product_ids = fields.Many2many('product.product', 'product_accessory_rel', 'src_id', 'dest_id', string='Accessory Products', help='Appear on the shopping cart')
    website_size_x = fields.Integer('Size X', default=1)
    website_size_y = fields.Integer('Size Y', default=1)
    website_style_ids = fields.Many2many('product.style', string='Styles')

    @api.model
    def _defaults_website_sequence(self, *l, **kwargs):
        return self.search([], order='website_sequence desc', limit=1).website_sequence

    website_sequence = fields.Integer('Sequence', help="Determine the display order in the Website E-commerce")
    public_categ_ids = fields.Many2many('product.public.category', string='Public Category', help="Those categories are used to group similar products for e-commerce.")

    @api.multi
    def set_sequence_top(self):
        self.ensure_one()
        self.website_sequence = self.search([], order='website_sequence desc', limit=1).website_sequence + 1

    @api.multi
    def set_sequence_bottom(self):
        self.ensure_one()
        self.website_sequence = self.search([], order='website_sequence', limit=1).website_sequence - 1

    @api.multi
    def set_sequence_up(self):
        self.ensure_one()
        prev = self.search([('website_sequence', '>', self.website_sequence), ('website_published', '=', self.website_published)], order='website_sequence', limit=1)
        if prev:
            prev.website_sequence = self.website_sequence
            self.website_sequence = prev.website_sequence
            return True
        else:
            return self.set_sequence_top()

    @api.multi
    def set_sequence_down(self):
        self.ensure_one()
        next = self.search([('website_sequence', '<', self.website_sequence), ('website_published', '=', self.website_published)], order='website_sequence desc', limit=1)
        if next:
            next.website_sequence = self.website_sequence
            self.website_sequence = next.website_sequence
            return True
        else:
            return self.set_sequence_bottom()


class ProductProduct(models.Model):
    _inherit = "product.product"

    # Wrapper for call_kw with inherits
    @api.multi
    def open_website_url(self):
        return self.env['product.template'].open_website_url(self.mapped('product_tmpl_id.id'))


class ProductAttribute(models.Model):
    _inherit = "product.attribute"

    type = fields.Selection([('radio', 'Radio'), ('select', 'Select'), ('color', 'Color'), ('hidden', 'Hidden')], default=lambda *a: 'radio')


class ProductAttribute_value(models.Model):
    _inherit = "product.attribute.value"

    color = fields.Char("HTML Color Index", help="Here you can set a specific HTML color index (e.g. #ff0000) to display the color on the website if the attibute type is 'Color'.")
