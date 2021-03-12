# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools
from collections import defaultdict

from odoo.addons import decimal_precision as dp

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, RedirectWarning, UserError
from odoo.osv import expression
from odoo.tools import pycompat


class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Product Template"
    _order = "name"

    def _get_default_category_id(self):
        if self._context.get('categ_id') or self._context.get('default_categ_id'):
            return self._context.get('categ_id') or self._context.get('default_categ_id')
        category = self.env.ref('product.product_category_all', raise_if_not_found=False)
        if not category:
            category = self.env['product.category'].search([], limit=1)
        if category:
            return category.id
        else:
            err_msg = _('You must define at least one product category in order to be able to create products.')
            redir_msg = _('Go to Internal Categories')
            raise RedirectWarning(err_msg, self.env.ref('product.product_category_action_form').id, redir_msg)

    def _get_default_uom_id(self):
        return self.env["uom.uom"].search([], limit=1, order='id').id

    name = fields.Char('Name', index=True, required=True, translate=True)
    sequence = fields.Integer('Sequence', default=1, help='Gives the sequence order when displaying a product list')
    description = fields.Text(
        'Description', translate=True)
    description_purchase = fields.Text(
        'Purchase Description', translate=True)
    description_sale = fields.Text(
        'Sale Description', translate=True,
        help="A description of the Product that you want to communicate to your customers. "
             "This description will be copied to every Sales Order, Delivery Order and Customer Invoice/Credit Note")
    type = fields.Selection([
        ('consu', 'Consumable'),
        ('service', 'Service')], string='Product Type', default='consu', required=True,
        help='A storable product is a product for which you manage stock. The Inventory app has to be installed.\n'
             'A consumable product is a product for which stock is not managed.\n'
             'A service is a non-material product you provide.')
    rental = fields.Boolean('Can be Rent')
    categ_id = fields.Many2one(
        'product.category', 'Product Category',
        change_default=True, default=_get_default_category_id,
        required=True, help="Select category for the current product")

    currency_id = fields.Many2one(
        'res.currency', 'Currency', compute='_compute_currency_id')
    cost_currency_id = fields.Many2one(
        'res.currency', 'Cost Currency', compute='_compute_cost_currency_id')

    # price fields
    # price: total template price, context dependent (partner, pricelist, quantity)
    price = fields.Float(
        'Price', compute='_compute_template_price', inverse='_set_template_price',
        digits=dp.get_precision('Product Price'))
    # list_price: catalog price, user defined
    list_price = fields.Float(
        'Sales Price', default=1.0,
        digits=dp.get_precision('Product Price'),
        help="Price at which the product is sold to customers.")
    # lst_price: catalog price for template, but including extra for variants
    lst_price = fields.Float(
        'Public Price', related='list_price', readonly=False,
        digits=dp.get_precision('Product Price'))
    standard_price = fields.Float(
        'Cost', compute='_compute_standard_price',
        inverse='_set_standard_price', search='_search_standard_price',
        digits=dp.get_precision('Product Price'), groups="base.group_user",
        help = "Cost used for stock valuation in standard price and as a first price to set in average/FIFO.")

    volume = fields.Float(
        'Volume', compute='_compute_volume', inverse='_set_volume',
        help="The volume in m3.", store=True)
    weight = fields.Float(
        'Weight', compute='_compute_weight', digits=dp.get_precision('Stock Weight'),
        inverse='_set_weight', store=True,
        help="The weight of the contents in Kg, not including any packaging, etc.")
    weight_uom_id = fields.Many2one('uom.uom', string='Weight Unit of Measure', compute='_compute_weight_uom_id')
    weight_uom_name = fields.Char(string='Weight unit of measure label', related='weight_uom_id.name', readonly=True)

    sale_ok = fields.Boolean('Can be Sold', default=True)
    purchase_ok = fields.Boolean('Can be Purchased', default=True)
    pricelist_id = fields.Many2one(
        'product.pricelist', 'Pricelist', store=False,
        help='Technical field. Used for searching on pricelists, not stored in database.')
    uom_id = fields.Many2one(
        'uom.uom', 'Unit of Measure',
        default=_get_default_uom_id, required=True,
        help="Default unit of measure used for all stock operations.")
    uom_name = fields.Char(string='Unit of Measure Name', related='uom_id.name', readonly=True)
    uom_po_id = fields.Many2one(
        'uom.uom', 'Purchase Unit of Measure',
        default=_get_default_uom_id, required=True,
        help="Default unit of measure used for purchase orders. It must be in the same category as the default unit of measure.")
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env['res.company']._company_default_get('product.template'), index=1)
    packaging_ids = fields.One2many(
        'product.packaging', string="Product Packages", compute="_compute_packaging_ids", inverse="_set_packaging_ids",
        help="Gives the different ways to package the same product.")
    seller_ids = fields.One2many('product.supplierinfo', 'product_tmpl_id', 'Vendors', help="Define vendor pricelists.")
    variant_seller_ids = fields.One2many('product.supplierinfo', 'product_tmpl_id')

    active = fields.Boolean('Active', default=True, help="If unchecked, it will allow you to hide the product without removing it.")
    color = fields.Integer('Color Index')

    is_product_variant = fields.Boolean(string='Is a product variant', compute='_compute_is_product_variant')
    attribute_line_ids = fields.One2many('product.template.attribute.line', 'product_tmpl_id', 'Product Attributes')

    valid_product_template_attribute_line_ids = fields.Many2many('product.template.attribute.line',
        compute="_compute_valid_attributes", string='Valid Product Attribute Lines', help="Technical compute")
    valid_product_attribute_value_ids = fields.Many2many('product.attribute.value',
        compute="_compute_valid_attributes", string='Valid Product Attribute Values', help="Technical compute")
    valid_product_attribute_ids = fields.Many2many('product.attribute',
        compute="_compute_valid_attributes", string='Valid Product Attributes', help="Technical compute")
    # wnva = without no_variant attributes
    valid_product_template_attribute_line_wnva_ids = fields.Many2many('product.template.attribute.line',
        compute="_compute_valid_attributes", string='Valid Product Attribute Lines Without No Variant Attributes', help="Technical compute")
    valid_product_attribute_value_wnva_ids = fields.Many2many('product.attribute.value',
        compute="_compute_valid_attributes", string='Valid Product Attribute Values Without No Variant Attributes', help="Technical compute")
    valid_product_attribute_wnva_ids = fields.Many2many('product.attribute',
        compute="_compute_valid_attributes", string='Valid Product Attributes Without No Variant Attributes', help="Technical compute")
    # valid_archived_variant_ids deprecated
    valid_archived_variant_ids = fields.Many2many('product.product',
        compute="_compute_valid_archived_variant_ids", string='Valid Archived Variants', help="Technical compute")
    # valid_existing_variant_ids deprecated
    valid_existing_variant_ids = fields.Many2many('product.product',
        compute="_compute_valid_existing_variant_ids", string='Valid Existing Variants', help="Technical compute")

    product_variant_ids = fields.One2many('product.product', 'product_tmpl_id', 'Products', required=True)
    # performance: product_variant_id provides prefetching on the first product variant only
    product_variant_id = fields.Many2one('product.product', 'Product', compute='_compute_product_variant_id')

    product_variant_count = fields.Integer(
        '# Product Variants', compute='_compute_product_variant_count')

    # related to display product product information if is_product_variant
    barcode = fields.Char('Barcode', oldname='ean13', related='product_variant_ids.barcode', readonly=False)
    default_code = fields.Char(
        'Internal Reference', compute='_compute_default_code',
        inverse='_set_default_code', store=True)

    item_ids = fields.One2many('product.pricelist.item', 'product_tmpl_id', 'Pricelist Items')

    # image: all image fields are base64 encoded and PIL-supported
    image = fields.Binary(
        "Image", attachment=True,
        help="This field holds the image used as image for the product, limited to 1024x1024px.")
    image_medium = fields.Binary(
        "Medium-sized image", attachment=True,
        help="Medium-sized image of the product. It is automatically "
             "resized as a 128x128px image, with aspect ratio preserved, "
             "only when the image exceeds one of those sizes. Use this field in form views or some kanban views.")
    image_small = fields.Binary(
        "Small-sized image", attachment=True,
        help="Small-sized image of the product. It is automatically "
             "resized as a 64x64px image, with aspect ratio preserved. "
             "Use this field anywhere a small image is required.")

    @api.depends('product_variant_ids')
    def _compute_product_variant_id(self):
        for p in self:
            p.product_variant_id = p.product_variant_ids[:1].id

    @api.multi
    def _compute_currency_id(self):
        main_company = self.env['res.company']._get_main_company()
        for template in self:
            template.currency_id = template.company_id.sudo().currency_id.id or main_company.currency_id.id

    def _compute_cost_currency_id(self):
        for template in self:
            template.cost_currency_id = self.env.user.company_id.currency_id.id

    @api.multi
    def _compute_template_price(self):
        prices = self._compute_template_price_no_inverse()
        for template in self:
            template.price = prices.get(template.id, 0.0)

    @api.multi
    def _compute_template_price_no_inverse(self):
        """The _compute_template_price writes the 'list_price' field with an inverse method
        This method allows computing the price without writing the 'list_price'
        """
        prices = {}
        pricelist_id_or_name = self._context.get('pricelist')
        if pricelist_id_or_name:
            pricelist = None
            partner = self.env.context.get('partner')
            quantity = self.env.context.get('quantity', 1.0)

            # Support context pricelists specified as display_name or ID for compatibility
            if isinstance(pricelist_id_or_name, pycompat.string_types):
                pricelist_data = self.env['product.pricelist'].name_search(pricelist_id_or_name, operator='=', limit=1)
                if pricelist_data:
                    pricelist = self.env['product.pricelist'].browse(pricelist_data[0][0])
            elif isinstance(pricelist_id_or_name, pycompat.integer_types):
                pricelist = self.env['product.pricelist'].browse(pricelist_id_or_name)

            if pricelist:
                quantities = [quantity] * len(self)
                partners = [partner] * len(self)
                prices = pricelist.get_products_price(self, quantities, partners)

        return prices

    @api.multi
    def _set_template_price(self):
        if self._context.get('uom'):
            for template in self:
                value = self.env['uom.uom'].browse(self._context['uom'])._compute_price(template.price, template.uom_id)
                template.write({'list_price': value})
        else:
            self.write({'list_price': self.price})

    @api.depends('product_variant_ids', 'product_variant_ids.standard_price')
    def _compute_standard_price(self):
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.standard_price = template.product_variant_ids.standard_price
        for template in (self - unique_variants):
            template.standard_price = 0.0

    @api.one
    def _set_standard_price(self):
        if len(self.product_variant_ids) == 1:
            self.product_variant_ids.standard_price = self.standard_price

    def _search_standard_price(self, operator, value):
        products = self.env['product.product'].search([('standard_price', operator, value)], limit=None)
        return [('id', 'in', products.mapped('product_tmpl_id').ids)]

    @api.depends('product_variant_ids', 'product_variant_ids.volume')
    def _compute_volume(self):
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.volume = template.product_variant_ids.volume
        for template in (self - unique_variants):
            template.volume = 0.0

    @api.one
    def _set_volume(self):
        if len(self.product_variant_ids) == 1:
            self.product_variant_ids.volume = self.volume

    @api.depends('product_variant_ids', 'product_variant_ids.weight')
    def _compute_weight(self):
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.weight = template.product_variant_ids.weight
        for template in (self - unique_variants):
            template.weight = 0.0

    def _compute_is_product_variant(self):
        for template in self:
            template.is_product_variant = False

    @api.model
    def _get_weight_uom_id_from_ir_config_parameter(self):
        """ Get the unit of measure to interpret the `weight` field. By default, we considerer
        that weights are expressed in kilograms. Users can configure to express them in pounds
        by adding an ir.config_parameter record with "product.product_weight_in_lbs" as key
        and "1" as value.
        """
        get_param = self.env['ir.config_parameter'].sudo().get_param
        product_weight_in_lbs_param = get_param('product.weight_in_lbs')
        if product_weight_in_lbs_param == '1':
            return self.env.ref('uom.product_uom_lb')
        else:
            return self.env.ref('uom.product_uom_kgm')

    def _compute_weight_uom_id(self):
        weight_uom_id = self._get_weight_uom_id_from_ir_config_parameter()
        for product_template in self:
            product_template.weight_uom_id = weight_uom_id

    @api.one
    def _set_weight(self):
        if len(self.product_variant_ids) == 1:
            self.product_variant_ids.weight = self.weight

    @api.one
    @api.depends('product_variant_ids.product_tmpl_id')
    def _compute_product_variant_count(self):
        # do not pollute variants to be prefetched when counting variants
        self.product_variant_count = len(self.with_prefetch().product_variant_ids)

    @api.depends('product_variant_ids', 'product_variant_ids.default_code')
    def _compute_default_code(self):
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.default_code = template.product_variant_ids.default_code
        for template in (self - unique_variants):
            template.default_code = False

    @api.one
    def _set_default_code(self):
        if len(self.product_variant_ids) == 1:
            self.product_variant_ids.default_code = self.default_code

    @api.depends('product_variant_ids', 'product_variant_ids.packaging_ids')
    def _compute_packaging_ids(self):
        for p in self:
            if len(p.product_variant_ids) == 1:
                p.packaging_ids = p.product_variant_ids.packaging_ids

    def _set_packaging_ids(self):
        for p in self:
            if len(p.product_variant_ids) == 1:
                p.product_variant_ids.packaging_ids = p.packaging_ids

    @api.constrains('uom_id', 'uom_po_id')
    def _check_uom(self):
        if any(template.uom_id and template.uom_po_id and template.uom_id.category_id != template.uom_po_id.category_id for template in self):
            raise ValidationError(_('The default Unit of Measure and the purchase Unit of Measure must be in the same category.'))
        return True

    @api.constrains('attribute_line_ids')
    def _check_attribute_line(self):
        if any(len(template.attribute_line_ids) != len(template.attribute_line_ids.mapped('attribute_id')) for template in self):
            raise ValidationError(_('You cannot define two attribute lines for the same attribute.'))
        return True

    @api.onchange('uom_id')
    def _onchange_uom_id(self):
        if self.uom_id:
            self.uom_po_id = self.uom_id.id

    @api.model_create_multi
    def create(self, vals_list):
        ''' Store the initial standard price in order to be able to retrieve the cost of a product template for a given date'''
        # TDE FIXME: context brol
        for vals in vals_list:
            tools.image_resize_images(vals)
        templates = super(ProductTemplate, self).create(vals_list)
        if "create_product_product" not in self._context:
            templates.with_context(create_from_tmpl=True).create_variant_ids()

        # This is needed to set given values to first variant after creation
        for template, vals in pycompat.izip(templates, vals_list):
            related_vals = {}
            if vals.get('barcode'):
                related_vals['barcode'] = vals['barcode']
            if vals.get('default_code'):
                related_vals['default_code'] = vals['default_code']
            if vals.get('standard_price'):
                related_vals['standard_price'] = vals['standard_price']
            if vals.get('volume'):
                related_vals['volume'] = vals['volume']
            if vals.get('weight'):
                related_vals['weight'] = vals['weight']
            # Please do forward port
            if vals.get('packaging_ids'):
                related_vals['packaging_ids'] = vals['packaging_ids']
            if related_vals:
                template.write(related_vals)

        return templates

    @api.multi
    def write(self, vals):
        tools.image_resize_images(vals)
        res = super(ProductTemplate, self).write(vals)
        if 'attribute_line_ids' in vals or vals.get('active'):
            self.create_variant_ids()
        if 'active' in vals and not vals.get('active'):
            self.with_context(active_test=False).mapped('product_variant_ids').write({'active': vals.get('active')})
        return res

    @api.multi
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        # TDE FIXME: should probably be copy_data
        self.ensure_one()
        if default is None:
            default = {}
        if 'name' not in default:
            default['name'] = _("%s (copy)") % self.name
        return super(ProductTemplate, self).copy(default=default)

    @api.multi
    def name_get(self):
        # Prefetch the fields used by the `name_get`, so `browse` doesn't fetch other fields
        self.browse(self.ids).read(['name', 'default_code'])
        return [(template.id, '%s%s' % (template.default_code and '[%s] ' % template.default_code or '', template.name))
                for template in self]

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        # Only use the product.product heuristics if there is a search term and the domain
        # does not specify a match on `product.template` IDs.
        if not name or any(term[0] == 'id' for term in (args or [])):
            return super(ProductTemplate, self)._name_search(name=name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)

        Product = self.env['product.product']
        templates = self.browse([])
        domain_no_variant = [('product_variant_ids', '=', False)]
        while True:
            domain = templates and [('product_tmpl_id', 'not in', templates.ids)] or []
            args = args if args is not None else []
            products_ns = Product._name_search(name, args+domain, operator=operator, name_get_uid=name_get_uid)
            products = Product.browse([x[0] for x in products_ns])
            templates |= products.mapped('product_tmpl_id')
            current_round_templates = self.browse([])
            if not products:
                domain_template = args + domain_no_variant + (templates and [('id', 'not in', templates.ids)] or [])
                template_ns = super(ProductTemplate, self)._name_search(name=name, args=domain_template, operator=operator, limit=limit, name_get_uid=name_get_uid)
                current_round_templates |= self.browse([ns[0] for ns in template_ns])
                templates |= current_round_templates
            if (not products and not current_round_templates) or (limit and (len(templates) > limit)):
                break

        # re-apply product.template order + name_get
        return super(ProductTemplate, self)._name_search(
            '', args=[('id', 'in', list(set(templates.ids)))],
            operator='ilike', limit=limit, name_get_uid=name_get_uid)

    @api.multi
    def price_compute(self, price_type, uom=False, currency=False, company=False):
        # TDE FIXME: delegate to template or not ? fields are reencoded here ...
        # compatibility about context keys used a bit everywhere in the code
        if not uom and self._context.get('uom'):
            uom = self.env['uom.uom'].browse(self._context['uom'])
        if not currency and self._context.get('currency'):
            currency = self.env['res.currency'].browse(self._context['currency'])

        templates = self
        if price_type == 'standard_price':
            # standard_price field can only be seen by users in base.group_user
            # Thus, in order to compute the sale price from the cost for users not in this group
            # We fetch the standard price as the superuser
            templates = self.with_context(force_company=company and company.id or self._context.get('force_company', self.env.user.company_id.id)).sudo()
        if not company:
            if self._context.get('force_company'):
                company = self.env['res.company'].browse(self._context['force_company'])
            else:
                company = self.env.user.company_id
        date = self.env.context.get('date') or fields.Date.today()

        prices = dict.fromkeys(self.ids, 0.0)
        for template in templates:
            prices[template.id] = template[price_type] or 0.0
            # yes, there can be attribute values for product template if it's not a variant YET
            # (see field product.attribute create_variant)
            if price_type == 'list_price' and self._context.get('current_attributes_price_extra'):
                # we have a list of price_extra that comes from the attribute values, we need to sum all that
                prices[template.id] += sum(self._context.get('current_attributes_price_extra'))

            if uom:
                prices[template.id] = template.uom_id._compute_price(prices[template.id], uom)

            # Convert from current user company currency to asked one
            # This is right cause a field cannot be in more than one currency
            if currency:
                prices[template.id] = template.currency_id._convert(prices[template.id], currency, company, date)

        return prices

    # compatibility to remove after v10 - DEPRECATED
    @api.model
    def _price_get(self, products, ptype='list_price'):
        return products.price_compute(ptype)

    @api.multi
    def create_variant_ids(self):
        Product = self.env["product.product"]

        for tmpl_id in self.with_context(active_test=False):
            # Handle the variants for each template separately. This will be
            # less efficient when called on a lot of products with few variants
            # but it is better when there's a lot of variants on one template.
            variants_to_create = []
            variants_to_activate = self.env['product.product']
            variants_to_unlink = self.env['product.product']
            # adding an attribute with only one value should not recreate product
            # write this attribute on every product to make sure we don't lose them
            variant_alone = tmpl_id._get_valid_product_template_attribute_lines().filtered(lambda line: line.attribute_id.create_variant == 'always' and len(line.value_ids) == 1).mapped('value_ids')
            for value_id in variant_alone:
                updated_products = tmpl_id.product_variant_ids.filtered(lambda product: value_id.attribute_id not in product.mapped('attribute_value_ids.attribute_id'))
                updated_products.write({'attribute_value_ids': [(4, value_id.id)]})

            # Determine which product variants need to be created based on the attribute
            # configuration. If any attribute is set to generate variants dynamically, skip the
            # process.
            # Technical note: if there is no attribute, a variant is still created because
            # 'not any([])' and 'set([]) not in set([])' are True.
            if not tmpl_id.has_dynamic_attributes():
                # Iterator containing all possible `product.attribute.value` combination
                # The iterator is used to avoid MemoryError in case of a huge number of combination.
                all_variants = itertools.product(*(
                    line.value_ids.ids for line in tmpl_id.valid_product_template_attribute_line_wnva_ids
                ))
                # Set containing existing `product.attribute.value` combination
                existing_variants = {
                    frozenset(variant.attribute_value_ids.ids)
                    for variant in tmpl_id.product_variant_ids
                }
                # For each possible variant, create if it doesn't exist yet.
                for value_ids in all_variants:
                    value_ids = frozenset(value_ids)
                    if value_ids not in existing_variants:
                        variants_to_create.append({
                            'product_tmpl_id': tmpl_id.id,
                            'attribute_value_ids': [(6, 0, list(value_ids))],
                            'active': tmpl_id.active,
                        })
                        if len(variants_to_create) > 1000:
                            raise UserError(_(
                                'The number of variants to generate is too high. '
                                'You should either not generate variants for each combination or generate them on demand from the sales order. '
                                'To do so, open the form view of attributes and change the mode of *Create Variants*.'))

            # Check existing variants if any needs to be activated or unlinked.
            # - if the product is not active and has valid attributes and attribute values, it
            #   should be activated
            # - if the product does not have valid attributes or attribute values, it should be
            #   deleted
            valid_value_ids = tmpl_id.valid_product_attribute_value_wnva_ids
            valid_attribute_ids = tmpl_id.valid_product_attribute_wnva_ids
            seen_attributes = set(p.attribute_value_ids for p in tmpl_id.product_variant_ids if p.active)
            for product_id in tmpl_id.product_variant_ids:
                if product_id._has_valid_attributes(valid_attribute_ids, valid_value_ids):
                    if not product_id.active and product_id.attribute_value_ids not in seen_attributes:
                        variants_to_activate += product_id
                        seen_attributes.add(product_id.attribute_value_ids)
                else:
                    variants_to_unlink += product_id

            if variants_to_activate:
                variants_to_activate.write({'active': True})

            # create new products
            if variants_to_create:
                Product.create(variants_to_create)

            # Avoid access errors in case the products is shared amongst companies but the underlying
            # objects are not. If unlink fails because of an AccessError (e.g. while recomputing
            # fields), the 'write' call will fail as well for the same reason since the field has
            # been set to recompute.
            if variants_to_unlink:
                variants_to_unlink.check_access_rights('unlink')
                variants_to_unlink.check_access_rule('unlink')
                variants_to_unlink.check_access_rights('write')
                variants_to_unlink.check_access_rule('write')
                variants_to_unlink = variants_to_unlink.sudo()
            # unlink or inactive product
            # try in batch first because it is much faster
            try:
                with self._cr.savepoint(), tools.mute_logger('odoo.sql_db'):
                    variants_to_unlink.unlink()
            except Exception:
                # fall back to one by one if batch is not possible
                for variant in variants_to_unlink:
                    try:
                        with self._cr.savepoint(), tools.mute_logger('odoo.sql_db'):
                            variant.unlink()
                    # We catch all kind of exception to be sure that the operation doesn't fail.
                    except Exception:
                        # Note: this can still fail if something is preventing from archiving.
                        # This is the case from existing stock reordering rules.
                        variant.write({'active': False})

        # prefetched o2m have to be reloaded (because of active_test)
        # (eg. product.template: product_variant_ids)
        # We can't rely on existing invalidate_cache because of the savepoint.
        self.invalidate_cache()
        return True

    def has_dynamic_attributes(self):
        """Return whether this `product.template` has at least one dynamic
        attribute.

        :return: True if at least one dynamic attribute, False otherwise
        :rtype: bool
        """
        self.ensure_one()
        return any(a.create_variant == 'dynamic' for a in self._get_valid_product_attributes())

    @api.multi
    def _compute_valid_attributes(self):
        """A product template attribute line is considered valid if it has at
        least one possible value.

        Those with only one value are considered valid, even though they should
        not appear on the configurator itself (unless they have an is_custom
        value to input), indeed single value attributes can be used to filter
        products among others based on that attribute/value.

        A product attribute value is considered valid for a template if it is
        defined on a product template attribute line.

        A product attribute is considered valid for a template if it
        has at least one possible value set on the template.

        For what is considered an archived variant, see `_has_valid_attributes`.
        """
        # prefetch
        self.mapped('attribute_line_ids.value_ids.id')
        self.mapped('attribute_line_ids.attribute_id.create_variant')

        for record in self:
            record.valid_product_template_attribute_line_ids = record.attribute_line_ids.filtered(lambda ptal: ptal.value_ids)
            record.valid_product_template_attribute_line_wnva_ids = record.valid_product_template_attribute_line_ids._without_no_variant_attributes()

            record.valid_product_attribute_value_ids = record.valid_product_template_attribute_line_ids.mapped('value_ids')
            record.valid_product_attribute_value_wnva_ids = record.valid_product_template_attribute_line_wnva_ids.mapped('value_ids')

            record.valid_product_attribute_ids = record.valid_product_template_attribute_line_ids.mapped('attribute_id')
            record.valid_product_attribute_wnva_ids = record.valid_product_template_attribute_line_wnva_ids.mapped('attribute_id')

    @api.multi
    def _compute_valid_archived_variant_ids(self):
        """This compute is done outside of `_compute_valid_attributes` because
        it is often not needed, and it can be very bad on performance."""
        archived_variants = self.env['product.product'].search([('product_tmpl_id', 'in', self.ids), ('active', '=', False)])
        for record in self:
            valid_value_ids = record.valid_product_attribute_value_wnva_ids
            valid_attribute_ids = record.valid_product_attribute_wnva_ids

            record.valid_archived_variant_ids = archived_variants.filtered(
                lambda v: v.product_tmpl_id == record and v._has_valid_attributes(valid_attribute_ids, valid_value_ids)
            )

    @api.multi
    def _compute_valid_existing_variant_ids(self):
        """This compute is done outside of `_compute_valid_attributes` because
        it is often not needed, and it can be very bad on performance."""
        existing_variants = self.env['product.product'].search([('product_tmpl_id', 'in', self.ids), ('active', '=', True)])
        for record in self:

            valid_value_ids = record.valid_product_attribute_value_wnva_ids
            valid_attribute_ids = record.valid_product_attribute_wnva_ids

            record.valid_existing_variant_ids = existing_variants.filtered(
                lambda v: v.product_tmpl_id == record and v._has_valid_attributes(valid_attribute_ids, valid_value_ids)
            )

    @api.multi
    def _get_valid_product_template_attribute_lines(self):
        """deprecated, use `valid_product_template_attribute_line_ids`"""
        self.ensure_one()
        return self.valid_product_template_attribute_line_ids

    @api.multi
    def _get_valid_product_attributes(self):
        """deprecated, use `valid_product_attribute_ids`"""
        self.ensure_one()
        return self.valid_product_attribute_ids

    @api.multi
    def _get_valid_product_attribute_values(self):
        """deprecated, use `valid_product_attribute_value_ids`"""
        self.ensure_one()
        return self.valid_product_attribute_value_ids

    @api.multi
    def _get_possible_variants(self, parent_combination=None):
        """Return the existing variants that are possible.

        For dynamic attributes, it will only return the variants that have been
        created already. For no_variant attributes, it will return an empty
        recordset because the variants themselves are not a full combination.
        If there are a lot of variants, this method might be slow. Even if there
        aren't too many variants, for performance reasons, do not call this
        method in a loop over the product templates.

        Therefore this method has a very restricted reasonable use case and you
        should strongly consider doing things differently if you consider using
        this method.

        :param parent_combination: combination from which `self` is an
            optional or accessory product.
        :type parent_combination: recordset `product.template.attribute.value`

        :return: the existing variants that are possible.
        :rtype: recordset of `product.product`
        """
        self.ensure_one()
        return self.product_variant_ids.filtered(lambda p: p._is_variant_possible(parent_combination))

    @api.multi
    def get_filtered_variants(self, reference_product=None):
        """deprecated, use _get_possible_variants instead"""
        self.ensure_one()

        parent_combination = self.env['product.template.attribute.value']

        if reference_product:
            # append the reference_product if provided
            parent_combination |= reference_product.product_template_attribute_value_ids
            if reference_product.env.context.get('no_variant_attribute_values'):
                # Add "no_variant" attribute values' exclusions
                # They are kept in the context since they are not linked to this product variant
                parent_combination |= reference_product.env.context.get('no_variant_attribute_values')
        return self._get_possible_variants(parent_combination)

    @api.multi
    def _get_attribute_exclusions(self, parent_combination=None):
        """Return the list of attribute exclusions of a product.

        :param parent_combination: the combination from which
            `self` is an optional or accessory product. Indeed exclusions
            rules on one product can concern another product.
        :type parent_combination: recordset `product.template.attribute.value`

        :return: dict of exclusions
            - exclusions: from this product itself
            - parent_combination: ids of the given parent_combination
            - parent_exclusions: from the parent_combination
            - archived_combinations: deprecated
            - existing_combinations: deprecated
            - has_dynamic_attributes: deprecated
            - no_variant_product_template_attribute_value_ids: deprecated
        """
        self.ensure_one()
        parent_combination = parent_combination or self.env['product.template.attribute.value']
        return {
            'exclusions': self._get_own_attribute_exclusions(),
            'parent_exclusions': self._get_parent_attribute_exclusions(parent_combination),
            'parent_combination': parent_combination.ids,
            'archived_combinations': [],
            'has_dynamic_attributes': self.has_dynamic_attributes(),
            'existing_combinations': [],
            'no_variant_product_template_attribute_value_ids': [],
        }

    @api.multi
    def _get_own_attribute_exclusions(self):
        """Get exclusions coming from the current template.

        Dictionnary, each ptav is a key, and for each of them the value is
        an array with the other ptav that they exclude (empty if no exclusion).
        """
        self.ensure_one()
        product_template_attribute_values = self._get_valid_product_template_attribute_lines().mapped('product_template_value_ids')
        return {
            ptav.id: [
                value_id
                for filter_line in ptav.exclude_for.filtered(
                    lambda filter_line: filter_line.product_tmpl_id == self
                ) for value_id in filter_line.value_ids.ids
            ]
            for ptav in product_template_attribute_values
        }

    @api.multi
    def _get_parent_attribute_exclusions(self, parent_combination):
        """Get exclusions coming from the parent combination.

        Array, each element is a ptav that is excluded because of the parent.
        """
        self.ensure_one()
        if not parent_combination:
            return []

        # Search for exclusions without attribute value. This means that the template is not
        # compatible with the parent combination. If such an exclusion is found, it means that all
        # attribute values are excluded.
        if parent_combination:
            exclusions = self.env['product.template.attribute.exclusion'].search([
                ('product_tmpl_id', '=', self.id),
                ('value_ids', '=', False),
                ('product_template_attribute_value_id', 'in', parent_combination.ids),
            ], limit=1)
            if exclusions:
                return self.mapped('attribute_line_ids.product_template_value_ids').ids

        return [
            value_id
            for filter_line in parent_combination.mapped('exclude_for').filtered(
                lambda filter_line: filter_line.product_tmpl_id == self
            ) for value_id in filter_line.value_ids.ids
        ]

    @api.multi
    def _get_archived_combinations(self):
        """Deprecated"""
        self.ensure_one()
        return [archived_variant.product_template_attribute_value_ids.ids
            for archived_variant in self.valid_archived_variant_ids]

    @api.multi
    def _get_existing_combinations(self):
        """Deprecated"""
        self.ensure_one()
        return [variant.product_template_attribute_value_ids.ids
            for variant in self.valid_existing_variant_ids]

    @api.multi
    def _get_no_variant_product_template_attribute_values(self):
        """Deprecated"""
        self.ensure_one()
        product_template_attribute_values = self._get_valid_product_template_attribute_lines().mapped('product_template_value_ids')
        return product_template_attribute_values.filtered(
            lambda v: v.attribute_id.create_variant == 'no_variant'
        ).ids

    @api.multi
    def _is_combination_possible(self, combination, parent_combination=None):
        """
        The combination is possible if it is not excluded by any rule
        coming from the current template, not excluded by any rule from the
        parent_combination (if given), and there should not be any archived
        variant with the exact same combination.

        If the template does not have any dynamic attribute, the combination
        is also not possible if the matching variant has been deleted.

        Moreover the attributes of the combination must excatly match the
        attributes allowed on the template.

        :param combination: the combination to check for possibility
        :type combination: recordset `product.template.attribute.value`

        :param parent_combination: combination from which `self` is an
            optional or accessory product.
        :type parent_combination: recordset `product.template.attribute.value`

        :return: whether the combination is possible
        :rtype: bool
        """
        self.ensure_one()

        if len(combination) != len(self.valid_product_template_attribute_line_ids):
            # number of attribute values passed is different than the
            # configuration of attributes on the template
            return False

        if self.valid_product_attribute_ids != combination.mapped('attribute_id'):
            # combination has different attributes than the ones configured on the template
            return False

        if self.valid_product_attribute_value_ids < combination.mapped('product_attribute_value_id'):
            # combination has different values than the ones configured on the template
            return False

        variant = self._get_variant_for_combination(combination)

        if self.has_dynamic_attributes():
            if variant and not variant.active:
                # dynamic and the variant has been archived
                return False
        else:
            if not variant or not variant.active:
                # not dynamic, the variant has been archived or deleted
                return False

        exclusions = self._get_own_attribute_exclusions()
        if exclusions:
            # exclude if the current value is in an exclusion,
            # and the value excluding it is also in the combination
            for ptav in combination:
                for exclusion in exclusions.get(ptav.id):
                    if exclusion in combination.ids:
                        return False

        parent_exclusions = self._get_parent_attribute_exclusions(parent_combination)
        if parent_exclusions:
            for exclusion in parent_exclusions:
                if exclusion in combination.ids:
                    return False

        return True

    @api.multi
    def _get_variant_for_combination(self, combination):
        """Get the variant matching the combination.

        All of the values in combination must be present in the variant, and the
        variant should not have more attributes. Ignore the attributes that are
        not supposed to create variants.

        :param combination: recordset of `product.template.attribute.value`

        :return: the variant if found, else empty
        :rtype: recordset `product.product`
        """
        self.ensure_one()

        filtered_combination = combination._without_no_variant_attributes()
        attribute_values = filtered_combination.mapped('product_attribute_value_id')
        return self.env['product.product'].browse(self._get_variant_id_for_combination(attribute_values))

    @api.multi
    @tools.ormcache('self', 'attribute_values')
    def _get_variant_id_for_combination(self, attribute_values):
        """See `_get_variant_for_combination`. This method returns an ID
        so it can be cached."""
        self.ensure_one()
        # If there are a lot of variants on this template, it is much faster to
        # build a query than using the existing o2m.
        domain = [('product_tmpl_id', '=', self.id)]
        for pav in attribute_values:
            domain = expression.AND([[('attribute_value_ids', 'in', pav.id)], domain])

        res = self.env['product.product'].with_context(active_test=False).search(domain, order='active DESC, id ASC')

        # The domain above is checking for the `product.attribute.value`, but we
        # need to make sure it's the same `product.template.attribute.value`.
        # Also there should theorically be only 0 or 1 but an existing database
        # might not be consistent so we need to make sure to take max 1.
        return res.filtered(
            lambda v: v.attribute_value_ids == attribute_values
        )[:1].id

    @api.multi
    @tools.ormcache('self')
    def _get_first_possible_variant_id(self):
        """See `_create_first_product_variant`. This method returns an ID
        so it can be cached."""
        self.ensure_one()
        return self._create_first_product_variant().id

    @api.multi
    def _get_first_possible_combination(self, parent_combination=None, necessary_values=None):
        """See `_get_possible_combinations` (one iteration).

        This method return the same result (empty recordset) if no
        combination is possible at all which would be considered a negative
        result, or if there are no attribute lines on the template in which
        case the "empty combination" is actually a possible combination.
        Therefore the result of this method when empty should be tested
        with `_is_combination_possible` if it's important to know if the
        resulting empty combination is actually possible or not.
        """
        return next(self._get_possible_combinations(parent_combination, necessary_values), self.env['product.template.attribute.value'])

    def _cartesian_product(self, product_template_attribute_values_per_line, parent_combination):
        """
        Generate all possible combination for attributes values (aka cartesian product).
        It is equivalent to itertools.product except it skips invalid partial combinations before they are complete.

        Imagine the cartesian product of 'A', 'CD' and range(1_000_000) and let's say that 'A' and 'C' are incompatible.
        If you use itertools.product or any normal cartesian product, you'll need to filter out of the final result
        the 1_000_000 combinations that start with 'A' and 'C' . Instead, This implementation will test if 'A' and 'C' are
        compatible before even considering range(1_000_000), skip it and and continue with combinations that start
        with 'A' and 'D'.

        It's necessary for performance reason because filtering out invalid combinations from standard Cartesian product
        can be extremely slow

        :param product_template_attribute_values_per_line: the values we want all the possibles combinations of.
        One list of values by attribute line
        :return: a generator of product template attribute value
        """
        if not product_template_attribute_values_per_line:
            return

        all_exclusions = {self.env['product.template.attribute.value'].browse(k):
                          self.env['product.template.attribute.value'].browse(v) for k, v in
                          self._get_own_attribute_exclusions().items()}
        # The following dict uses product template attribute values as keys
        # 0 means the value is acceptable, greater than 0 means it's rejected, it cannot be negative
        # Bear in mind that several values can reject the same value and the latter can only be included in the
        #  considered combination if no value rejects it.
        # This dictionary counts how many times each value is rejected.
        # Each time a value is included in the considered combination, the values it rejects are incremented
        # When a value is discarded from the considered combination, the values it rejects are decremented
        current_exclusions = defaultdict(int)
        for exclusion in self._get_parent_attribute_exclusions(parent_combination):
            current_exclusions[self.env['product.template.attribute.value'].browse(exclusion)] += 1
        partial_combination = self.env['product.template.attribute.value']

        # The following list reflects product_template_attribute_values_per_line
        # For each line, instead of a list of values, it contains the index of the selected value
        # -1 means no value has been picked for the line in the current (partial) combination
        value_index_per_line = [-1] * len(product_template_attribute_values_per_line)
        # determines which line line we're working on
        line_index = 0

        while True:
            current_line_values = product_template_attribute_values_per_line[line_index]
            current_ptav_index = value_index_per_line[line_index]
            current_ptav = current_line_values[current_ptav_index]

            # removing exclusions from current_ptav as we're removing it from partial_combination
            if current_ptav_index >= 0:
                for ptav_to_include_back in all_exclusions[current_ptav]:
                    current_exclusions[ptav_to_include_back] -= 1
                partial_combination -= current_ptav

            if current_ptav_index < len(current_line_values) - 1:
                # go to next value of current line
                value_index_per_line[line_index] += 1
                current_line_values = product_template_attribute_values_per_line[line_index]
                current_ptav_index = value_index_per_line[line_index]
                current_ptav = current_line_values[current_ptav_index]
            elif line_index != 0:
                # reset current line, and then go to previous line
                value_index_per_line[line_index] = - 1
                line_index -= 1
                continue
            else:
                # we're done if we must reset first line
                break

            # adding exclusions from current_ptav as we're incorporating it in partial_combination
            for ptav_to_exclude in all_exclusions[current_ptav]:
                current_exclusions[ptav_to_exclude] += 1
            partial_combination += current_ptav

            # test if included values excludes current value or if current value exclude included values
            if current_exclusions[current_ptav] or \
                    any(intersection in partial_combination for intersection in all_exclusions[current_ptav]):
                continue

            if line_index == len(product_template_attribute_values_per_line) - 1:
                # submit combination if we're on the last line
                yield partial_combination
            else:
                # else we go to the next line
                line_index += 1

    @api.multi
    def _get_possible_combinations(self, parent_combination=None, necessary_values=None):
        """Generator returning combinations that are possible, following the
        sequence of attributes and values.

        See `_is_combination_possible` for what is a possible combination.

        When encountering an impossible combination, try to change the value
        of attributes by starting with the further regarding their sequences.

        Ignore attributes that have no values.

        :param parent_combination: combination from which `self` is an
            optional or accessory product.
        :type parent_combination: recordset `product.template.attribute.value`

        :param necessary_values: values that must be in the returned combination
        :type necessary_values: recordset of `product.template.attribute.value`

        :return: the possible combinations
        :rtype: generator of recordset of `product.template.attribute.value`
        """
        self.ensure_one()

        if not self.active:
            return _("The product template is archived so no combination is possible.")

        necessary_values = necessary_values or self.env['product.template.attribute.value']
        necessary_attributes = necessary_values.mapped('attribute_id')

        attribute_lines = self.valid_product_template_attribute_line_ids.filtered(lambda ptal: ptal.attribute_id not in necessary_attributes)

        if not attribute_lines and self._is_combination_possible(necessary_values, parent_combination):
            yield necessary_values

        product_template_attribute_values_per_line = [
            attribute.product_template_value_ids
            for attribute in attribute_lines
        ]

        for partial_combination in self._cartesian_product(product_template_attribute_values_per_line, parent_combination):
            combination = partial_combination + necessary_values
            if self._is_combination_possible(combination, parent_combination):
                yield combination

        return _("There are no remaining possible combination.")

    @api.multi
    def _get_closest_possible_combination(self, combination):
        """See `_get_closest_possible_combinations` (one iteration).

        This method return the same result (empty recordset) if no
        combination is possible at all which would be considered a negative
        result, or if there are no attribute lines on the template in which
        case the "empty combination" is actually a possible combination.
        Therefore the result of this method when empty should be tested
        with `_is_combination_possible` if it's important to know if the
        resulting empty combination is actually possible or not.
        """
        return next(self._get_closest_possible_combinations(combination), self.env['product.template.attribute.value'])

    @api.multi
    def _get_closest_possible_combinations(self, combination):
        """Generator returning the possible combinations that are the closest to
        the given combination.

        If the given combination is incomplete, try to complete it.

        If the given combination is invalid, try to remove values from it before
        completing it.

        :param combination: the values to include if they are possible
        :type combination: recordset `product.template.attribute.value`

        :return: the possible combinations that are including as much
            elements as possible from the given combination.
        :rtype: generator of recordset of product.template.attribute.value
        """
        while True:
            res = self._get_possible_combinations(necessary_values=combination)
            try:
                # If there is at least one result for the given combination
                # we consider that combination set, and we yield all the
                # possible combinations for it.
                yield(next(res))
                for cur in res:
                    yield(cur)
                return _("There are no remaining closest combination.")
            except StopIteration:
                # There are no results for the given combination, we try to
                # progressively remove values from it.
                if not combination:
                    return _("There are no possible combination.")
                combination = combination[:-1]

    @api.multi
    def _get_current_company(self, **kwargs):
        """Get the most appropriate company for this product.

        If the company is set on the product, directly return it. Otherwise,
        fallback to a contextual company.

        :param kwargs: kwargs forwarded to the fallback method.

        :return: the most appropriate company for this product
        :rtype: recordset of one `res.company`
        """
        self.ensure_one()
        return self.company_id or self._get_current_company_fallback(**kwargs)

    @api.multi
    def _get_current_company_fallback(self, **kwargs):
        """Fallback to get the most appropriate company for this product.

        This should only be called from `_get_current_company` but is defined
        separately to allow override.

        The final fallback will be the current user's company.

        :return: the fallback company for this product
        :rtype: recordset of one `res.company`
        """
        self.ensure_one()
        return self.env.user.company_id

    @api.model
    def get_empty_list_help(self, help):
        self = self.with_context(
            empty_list_help_document_name=_("product"),
        )
        return super(ProductTemplate, self).get_empty_list_help(help)

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Products'),
            'template': '/product/static/xls/product_template.xls'
        }]
