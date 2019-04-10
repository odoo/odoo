# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, UserError
from odoo.addons.website.models import ir_http
from odoo.tools.translate import html_translate
from odoo.osv import expression


class ProductStyle(models.Model):
    _name = "product.style"
    _description = 'Product Style'

    name = fields.Char(string='Style Name', required=True)
    html_class = fields.Char(string='HTML Classes')


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    def _default_website(self):
        """ Find the first company's website, if there is one. """
        company_id = self.env.user.company_id.id

        if self._context.get('default_company_id'):
            company_id = self._context.get('default_company_id')

        domain = [('company_id', '=', company_id)]
        return self.env['website'].search(domain, limit=1)

    website_id = fields.Many2one('website', string="Website", default=_default_website)
    code = fields.Char(string='E-commerce Promotional Code', groups="base.group_user")
    selectable = fields.Boolean(help="Allow the end user to choose this price list")

    def clear_cache(self):
        # website._get_pl_partner_order() is cached to avoid to recompute at each request the
        # list of available pricelists. So, we need to invalidate the cache when
        # we change the config of website price list to force to recompute.
        website = self.env['website']
        website._get_pl_partner_order.clear_cache(website)

    @api.model
    def create(self, data):
        if data.get('company_id') and not data.get('website_id'):
            # l10n modules install will change the company currency, creating a
            # pricelist for that currency. Do not use user's company in that
            # case as module install are done with OdooBot (company 1)
            self = self.with_context(default_company_id=data['company_id'])
        res = super(ProductPricelist, self).create(data)
        self.clear_cache()
        return res

    @api.multi
    def write(self, data):
        res = super(ProductPricelist, self).write(data)
        if data.keys() & {'code', 'active', 'website_id', 'selectable'}:
            self._check_website_pricelist()
        self.clear_cache()
        return res

    @api.multi
    def unlink(self):
        res = super(ProductPricelist, self).unlink()
        self._check_website_pricelist()
        self.clear_cache()
        return res

    def _get_partner_pricelist_multi_search_domain_hook(self):
        domain = super(ProductPricelist, self)._get_partner_pricelist_multi_search_domain_hook()
        website = ir_http.get_request_website()
        if website:
            domain += self._get_website_pricelists_domain(website.id)
        return domain

    def _get_partner_pricelist_multi_filter_hook(self):
        res = super(ProductPricelist, self)._get_partner_pricelist_multi_filter_hook()
        website = ir_http.get_request_website()
        if website:
            res = res.filtered(lambda pl: pl._is_available_on_website(website.id))
        return res

    def _check_website_pricelist(self):
        for website in self.env['website'].search([]):
            if not website.pricelist_ids:
                raise UserError(_("With this action, '%s' website would not have any pricelist available.") % (website.name))

    @api.multi
    def _is_available_on_website(self, website_id):
        """ To be able to be used on a website, a pricelist should either:
        - Have its `website_id` set to current website (specific pricelist).
        - Have no `website_id` set and should be `selectable` (generic pricelist)
          or should have a `code` (generic promotion).

        Note: A pricelist without a website_id, not selectable and without a
              code is a backend pricelist.

        Change in this method should be reflected in `_get_website_pricelists_domain`.
        """
        self.ensure_one()
        return self.website_id.id == website_id or (not self.website_id and (self.selectable or self.sudo().code))

    def _get_website_pricelists_domain(self, website_id):
        ''' Check above `_is_available_on_website` for explanation.
        Change in this method should be reflected in `_is_available_on_website`.
        '''
        return [
            '|', ('website_id', '=', website_id),
            '&', ('website_id', '=', False),
            '|', ('selectable', '=', True), ('code', '!=', False),
        ]

    def _get_partner_pricelist_multi(self, partner_ids, company_id=None):
        ''' If `property_product_pricelist` is read from website, we should use
            the website's company and not the user's one.
            Passing a `company_id` to super will avoid using the current user's
            company.
        '''
        website = ir_http.get_request_website()
        if not company_id and website:
            company_id = website.company_id.id
        return super(ProductPricelist, self)._get_partner_pricelist_multi(partner_ids, company_id)

    @api.onchange('company_id')
    def _onchange_company_id(self):
        ''' Show only the company's website '''
        domain = self.company_id and [('company_id', '=', self.company_id.id)] or []
        return {'domain': {'website_id': domain}}

    @api.constrains('company_id', 'website_id')
    def _check_websites_in_company(self):
        '''Prevent misconfiguration multi-website/multi-companies.
           If the record has a company, the website should be from that company.
        '''
        for record in self.filtered(lambda pl: pl.website_id and pl.company_id):
            if record.website_id.company_id != record.company_id:
                raise ValidationError(_("Only the company's websites are allowed. \
                    Leave the Company field empty or select a website from that company."))


class ProductPublicCategory(models.Model):
    _name = "product.public.category"
    _inherit = ["website.seo.metadata", "website.multi.mixin"]
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
    image = fields.Binary(help="This field holds the image used as image for the category, limited to 1024x1024px.")
    website_description = fields.Html('Category Description', sanitize_attributes=False, translate=html_translate)
    image_medium = fields.Binary(string='Medium-sized image',
                                 help="Medium-sized image of the category. It is automatically "
                                 "resized as a 128x128px image, with aspect ratio preserved. "
                                 "Use this field in form views or some kanban views.")
    image_small = fields.Binary(string='Small-sized image',
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
    _inherit = ["product.template", "website.seo.metadata", 'website.published.multi.mixin', 'rating.mixin']
    _name = 'product.template'
    _mail_post_access = 'read'

    website_description = fields.Html('Description for the website', sanitize_attributes=False, translate=html_translate)
    alternative_product_ids = fields.Many2many('product.template', 'product_alternative_rel', 'src_id', 'dest_id',
                                               string='Alternative Products', help='Suggest alternatives to your customer'
                                               '(upsell strategy).Those product show up on the product page.')
    accessory_product_ids = fields.Many2many('product.product', 'product_accessory_rel', 'src_id', 'dest_id',
                                             string='Accessory Products', help='Accessories show up when the customer'
                                             'reviews the cart before payment (cross-sell strategy).')
    website_size_x = fields.Integer('Size X', default=1)
    website_size_y = fields.Integer('Size Y', default=1)
    website_style_ids = fields.Many2many('product.style', string='Styles')
    website_sequence = fields.Integer('Website Sequence', help="Determine the display order in the Website E-commerce",
                                      default=lambda self: self._default_website_sequence())
    public_categ_ids = fields.Many2many('product.public.category', string='Website Product Category',
                                        help="The product will be available in each mentioned e-commerce category. Go to"
                                        "Shop > Customize and enable 'E-commerce categories' to view all e-commerce categories.")

    product_template_image_ids = fields.One2many('product.image', 'product_tmpl_id', string="Extra Product Media", copy=True)

    @api.multi
    def _has_no_variant_attributes(self):
        """Return whether this `product.template` has at least one no_variant
        attribute.

        :return: True if at least one no_variant attribute, False otherwise
        :rtype: bool
        """
        self.ensure_one()
        return any(a.create_variant == 'no_variant' for a in self._get_valid_product_attributes())

    @api.multi
    def _has_is_custom_values(self):
        self.ensure_one()
        """Return whether this `product.template` has at least one is_custom
        attribute value.

        :return: True if at least one is_custom attribute value, False otherwise
        :rtype: bool
        """
        return any(v.is_custom for v in self._get_valid_product_attribute_values())

    @api.multi
    def _get_possible_variants_sorted(self, parent_combination=None):
        """Return the sorted recordset of variants that are possible.

        The order is based on the order of the attributes and their values.

        See `_get_possible_variants` for the limitations of this method with
        dynamic or no_variant attributes, and also for a warning about
        performances.

        :param parent_combination: combination from which `self` is an
            optional or accessory product
        :type parent_combination: recordset `product.template.attribute.value`

        :return: the sorted variants that are possible
        :rtype: recordset of `product.product`
        """
        self.ensure_one()

        def _sort_key_attribute_value(value):
            # if you change this order, keep it in sync with _order from `product.attribute`
            return (value.attribute_id.sequence, value.attribute_id.id)

        def _sort_key_variant(variant):
            """
                We assume all variants will have the same attributes, with only one value for each.
                    - first level sort: same as "product.attribute"._order
                    - second level sort: same as "product.attribute.value"._order
            """
            keys = []
            for attribute in variant.attribute_value_ids.sorted(_sort_key_attribute_value):
                # if you change this order, keep it in sync with _order from `product.attribute.value`
                keys.append(attribute.sequence)
                keys.append(attribute.id)
            return keys

        return self._get_possible_variants(parent_combination).sorted(_sort_key_variant)

    @api.multi
    def _get_combination_info(self, combination=False, product_id=False, add_qty=1, pricelist=False, parent_combination=False, only_template=False):
        """Override for website, where we want to:
            - take the website pricelist if no pricelist is set
            - apply the b2b/b2c setting to the result

        This will work when adding website_id to the context, which is done
        automatically when called from routes with website=True.
        """
        self.ensure_one()

        current_website = False

        if self.env.context.get('website_id'):
            current_website = self.env['website'].get_current_website()
            if not pricelist:
                pricelist = current_website.get_current_pricelist()

        combination_info = super(ProductTemplate, self)._get_combination_info(
            combination=combination, product_id=product_id, add_qty=add_qty, pricelist=pricelist,
            parent_combination=parent_combination, only_template=only_template)

        if self.env.context.get('website_id'):
            partner = self.env.user.partner_id
            company_id = current_website.company_id
            product = self.env['product.product'].browse(combination_info['product_id']) or self

            tax_display = self.env.user.has_group('account.group_show_line_subtotals_tax_excluded') and 'total_excluded' or 'total_included'
            taxes = partner.property_account_position_id.map_tax(product.sudo().taxes_id.filtered(lambda x: x.company_id == company_id), product, partner)

            # The list_price is always the price of one.
            quantity_1 = 1
            price = taxes.compute_all(combination_info['price'], pricelist.currency_id, quantity_1, product, partner)[tax_display]
            if pricelist.discount_policy == 'without_discount':
                list_price = taxes.compute_all(combination_info['list_price'], pricelist.currency_id, quantity_1, product, partner)[tax_display]
            else:
                list_price = price
            has_discounted_price = pricelist.currency_id.compare_amounts(list_price, price) == 1

            combination_info.update(
                price=price,
                list_price=list_price,
                has_discounted_price=has_discounted_price,
            )

        return combination_info

    @api.multi
    def _create_first_product_variant(self, log_warning=False):
        """Create if necessary and possible and return the first product
        variant for this template.

        :param log_warning: whether a warning should be logged on fail
        :type log_warning: bool

        :return: the first product variant or none
        :rtype: recordset of `product.product`
        """
        return self._create_product_variant(self._get_first_possible_combination(), log_warning)

    @api.multi
    def _get_current_company_fallback(self, **kwargs):
        """Override: if a website is set on the product or given, fallback to
        the company of the website. Otherwise use the one from parent method."""
        res = super(ProductTemplate, self)._get_current_company_fallback(**kwargs)
        website = self.website_id or kwargs.get('website')
        return website and website.company_id or res

    def _default_website_sequence(self):
        ''' We want new product to be the last (highest seq).
        Every product should ideally have an unique sequence.
        Default sequence (10000) should only be used for DB first product.
        As we don't resequence the whole tree (as `sequence` does), this field
        might have negative value.
        '''
        self._cr.execute("SELECT MAX(website_sequence) FROM %s" % self._table)
        max_sequence = self._cr.fetchone()[0]
        if max_sequence is None:
            return 10000
        return max_sequence + 5

    def set_sequence_top(self):
        min_sequence = self.sudo().search([], order='website_sequence ASC', limit=1)
        self.website_sequence = min_sequence.website_sequence - 5

    def set_sequence_bottom(self):
        max_sequence = self.sudo().search([], order='website_sequence DESC', limit=1)
        self.website_sequence = max_sequence.website_sequence + 5

    def set_sequence_up(self):
        previous_product_tmpl = self.sudo().search([
            ('website_sequence', '<', self.website_sequence),
            ('website_published', '=', self.website_published),
        ], order='website_sequence DESC', limit=1)
        if previous_product_tmpl:
            previous_product_tmpl.website_sequence, self.website_sequence = self.website_sequence, previous_product_tmpl.website_sequence
        else:
            self.set_sequence_top()

    def set_sequence_down(self):
        next_prodcut_tmpl = self.search([
            ('website_sequence', '>', self.website_sequence),
            ('website_published', '=', self.website_published),
        ], order='website_sequence ASC', limit=1)
        if next_prodcut_tmpl:
            next_prodcut_tmpl.website_sequence, self.website_sequence = self.website_sequence, next_prodcut_tmpl.website_sequence
        else:
            return self.set_sequence_bottom()

    def _default_website_meta(self):
        res = super(ProductTemplate, self)._default_website_meta()
        res['default_opengraph']['og:description'] = res['default_twitter']['twitter:description'] = self.description_sale
        res['default_opengraph']['og:title'] = res['default_twitter']['twitter:title'] = self.name
        res['default_opengraph']['og:image'] = res['default_twitter']['twitter:image'] = "/web/image/product.template/%s/image" % (self.id)
        res['default_meta_description'] = self.description_sale
        return res

    @api.multi
    def _compute_website_url(self):
        super(ProductTemplate, self)._compute_website_url()
        for product in self:
            product.website_url = "/shop/product/%s" % (product.id,)

    # ---------------------------------------------------------
    # Rating Mixin API
    # ---------------------------------------------------------

    @api.multi
    def _rating_domain(self):
        """ Only take the published rating into account to compute avg and count """
        domain = super(ProductTemplate, self)._rating_domain()
        return expression.AND([domain, [('website_published', '=', True)]])

    @api.multi
    def _get_images(self):
        """Return a list of records implementing `image.mixin` to
        display on the carousel on the website for this template.

        This returns a list and not a recordset because the records might be
        from different models (template and image).

        It contains in this order: the main image of the template and the
        Template Extra Images.
        """
        self.ensure_one()
        return [self] + list(self.product_template_image_ids)


class Product(models.Model):
    _inherit = "product.product"

    website_id = fields.Many2one(related='product_tmpl_id.website_id', readonly=False)

    product_variant_image_ids = fields.One2many('product.image', 'product_variant_id', string="Extra Variant Images")

    @api.multi
    def website_publish_button(self):
        self.ensure_one()
        return self.product_tmpl_id.website_publish_button()

    @api.multi
    def _get_images(self):
        """Return a list of records implementing `image.mixin` to
        display on the carousel on the website for this variant.

        This returns a list and not a recordset because the records might be
        from different models (template, variant and image).

        It contains in this order: the main image of the variant (if set), the
        Variant Extra Images, and the Template Extra Images.
        """
        self.ensure_one()
        variant_images = list(self.product_variant_image_ids)
        if self.image_raw_original:
            # if the main variant image is set, display it first
            variant_images = [self] + variant_images
        else:
            # If the main variant image is empty, it will fallback to template
            # image, in this case insert it after the other variant images, so
            # that all variant images are first and all template images last.
            variant_images = variant_images + [self]
        # [1:] to remove the main image from the template, we only display
        # the template extra images here
        return variant_images + self.product_tmpl_id._get_images()[1:]
