# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.tools import float_compare, groupby
from odoo.tools.image import is_image_size_above
from odoo.tools.misc import unique
from odoo.tools.sql import SQL


class ProductProduct(models.Model):
    _name = 'product.product'
    _description = "Product Variant"
    _inherits = {'product.template': 'product_tmpl_id'}
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'default_code, name, id'
    _check_company_domain = models.check_company_domain_parent_of

    # price_extra: catalog extra value only, sum of variant extra attributes
    price_extra = fields.Float(
        'Variant Price Extra', compute='_compute_product_price_extra',
        min_display_digits='Product Price',
        help="This is the sum of the extra price of all attributes")
    # lst_price: catalog value + extra, context dependent (uom)
    lst_price = fields.Float(
        'Sales Price', compute='_compute_product_lst_price',
        min_display_digits='Product Price', inverse='_set_product_lst_price',
        help="The sale price is managed from the product template. Click on the 'Configure Variants' button to set the extra attribute prices.")

    default_code = fields.Char('Internal Reference', index=True)
    code = fields.Char('Reference', compute='_compute_product_code')
    partner_ref = fields.Char('Customer Ref', compute='_compute_partner_ref')

    active = fields.Boolean(
        'Active', default=True,
        help="If unchecked, it will allow you to hide the product without removing it.")
    product_tmpl_id = fields.Many2one(
        'product.template', 'Product Template',
        bypass_search_access=True, index=True, ondelete="cascade", required=True)
    barcode = fields.Char(
        'Barcode', copy=False, index='btree_not_null',
        help="International Article Number used for product identification.")
    product_uom_ids = fields.One2many('product.uom', 'product_id', 'Unit Barcode', store=True)
    product_template_attribute_value_ids = fields.Many2many('product.template.attribute.value', relation='product_variant_combination', string="Attribute Values", ondelete='restrict')
    product_template_variant_value_ids = fields.Many2many('product.template.attribute.value', relation='product_variant_combination',
                                                          domain=[('attribute_line_id.value_count', '>', 1)], string="Variant Values", ondelete='restrict')
    combination_indices = fields.Char(compute='_compute_combination_indices', store=True, index=True)
    is_product_variant = fields.Boolean(compute='_compute_is_product_variant')

    standard_price = fields.Float(
        'Cost', company_dependent=True,
        min_display_digits='Product Price',
        groups="base.group_user",
        help="""Value of the product (automatically computed in AVCO).
        Used to value the product when the purchase cost is not known (e.g. inventory adjustment).
        Used to compute margins on sale orders.""")
    volume = fields.Float('Volume', digits='Volume')
    weight = fields.Float('Weight', digits='Stock Weight')

    pricelist_rule_ids = fields.One2many(
        string="Pricelist Rules",
        comodel_name='product.pricelist.item',
        inverse_name='product_id',
        compute='_compute_pricelist_rule_ids',
        inverse='_inverse_pricelist_rule_ids',
        readonly=False,
    )

    product_document_ids = fields.One2many(
        string="Documents",
        comodel_name='product.document',
        inverse_name='res_id',
        domain=lambda self: [('res_model', '=', self._name)])
    product_document_count = fields.Integer(
        string="Documents Count", compute='_compute_product_document_count')

    additional_product_tag_ids = fields.Many2many(
        string="Variant Tags",
        comodel_name='product.tag',
        relation='product_tag_product_product_rel',
        domain="[('id', 'not in', product_tag_ids)]",
    )
    all_product_tag_ids = fields.Many2many('product.tag', compute='_compute_all_product_tag_ids', search='_search_all_product_tag_ids')

    # all image fields are base64 encoded and PIL-supported

    # all image_variant fields are technical and should not be displayed to the user
    image_variant_1920 = fields.Image("Variant Image", max_width=1920, max_height=1920)

    # resized fields stored (as attachment) for performance
    image_variant_1024 = fields.Image("Variant Image 1024", related="image_variant_1920", max_width=1024, max_height=1024, store=True)
    image_variant_512 = fields.Image("Variant Image 512", related="image_variant_1920", max_width=512, max_height=512, store=True)
    image_variant_256 = fields.Image("Variant Image 256", related="image_variant_1920", max_width=256, max_height=256, store=True)
    image_variant_128 = fields.Image("Variant Image 128", related="image_variant_1920", max_width=128, max_height=128, store=True)
    can_image_variant_1024_be_zoomed = fields.Boolean("Can Variant Image 1024 be zoomed", compute='_compute_can_image_variant_1024_be_zoomed', store=True)

    # Computed fields that are used to create a fallback to the template if
    # necessary, it's recommended to display those fields to the user.
    image_1920 = fields.Image("Image", compute='_compute_image_1920', inverse='_set_image_1920')
    image_1024 = fields.Image("Image 1024", compute='_compute_image_1024')
    image_512 = fields.Image("Image 512", compute='_compute_image_512')
    image_256 = fields.Image("Image 256", compute='_compute_image_256')
    image_128 = fields.Image("Image 128", compute='_compute_image_128')
    can_image_1024_be_zoomed = fields.Boolean("Can Image 1024 be zoomed", compute='_compute_can_image_1024_be_zoomed')
    write_date = fields.Datetime(compute='_compute_write_date', store=True)

    # Ensure there is at most one active variant for each combination.
    # There could be no variant for a combination if using dynamic attributes.
    _combination_unique = models.UniqueIndex("(product_tmpl_id, combination_indices) WHERE active IS TRUE")

    is_favorite = fields.Boolean(related='product_tmpl_id.is_favorite', readonly=False, store=True)
    _is_favorite_index = models.Index("(is_favorite) WHERE is_favorite IS TRUE")
    is_in_selected_section_of_order = fields.Boolean(search='_search_is_in_selected_section_of_order')

    @api.depends('image_variant_1920', 'image_variant_1024')
    def _compute_can_image_variant_1024_be_zoomed(self):
        for record in self:
            record.can_image_variant_1024_be_zoomed = record.image_variant_1920 and is_image_size_above(record.image_variant_1920, record.image_variant_1024)

    def _set_template_field(self, template_field, variant_field):
        for record in self:
            if (
                # We are trying to remove a field from the variant even though it is already
                # not set on the variant, remove it from the template instead.
                (not record[template_field] and not record[variant_field])
                # We are trying to add a field to the variant, but the template field is
                # not set, write on the template instead.
                or (record[template_field] and not record.product_tmpl_id[template_field])
                # There is only one variant, always write on the template.
                or self.search_count([
                    ('product_tmpl_id', '=', record.product_tmpl_id.id),
                    ('active', '=', True),
                ]) <= 1
            ):
                record[variant_field] = False
                record.product_tmpl_id[template_field] = record[template_field]
            else:
                record[variant_field] = record[template_field]

    @api.depends('product_tmpl_id.pricelist_rule_ids')
    def _compute_pricelist_rule_ids(self):
        for product in self:
            if not product.id:
                product.pricelist_rule_ids = False
                continue
            product.pricelist_rule_ids = product.product_tmpl_id.pricelist_rule_ids.filtered(
                lambda rule: rule.product_id <= product,
            )

    def _inverse_pricelist_rule_ids(self):
        for product in self:
            template = product.product_tmpl_id
            template.pricelist_rule_ids = (
                product.pricelist_rule_ids
                # We have to manually keep the rules the current variant
                # wasn't aware of because they targeted other variants.
                | template.pricelist_rule_ids.filtered(
                    lambda rule: rule.product_id and rule.product_id != product
                )
            )

    @api.depends("product_tmpl_id.write_date")
    def _compute_write_date(self):
        """
        First, the purpose of this computation is to update a product's
        write_date whenever its template's write_date is updated.  Indeed,
        when a template's image is modified, updating its products'
        write_date will invalidate the browser's cache for the products'
        image, which may be the same as the template's.  This guarantees UI
        consistency.

        Second, the field 'write_date' is automatically updated by the
        framework when the product is modified.  The recomputation of the
        field supplements that behavior to keep the product's write_date
        up-to-date with its template's write_date.

        Third, the framework normally prevents us from updating write_date
        because it is a "magic" field.  However, the assignment inside the
        compute method is not subject to this restriction.  It therefore
        works as intended :-)
        """
        now = self.env.cr.now()
        for record in self:
            if not record.id:
                record.write_date = record._origin.write_date
                continue
            record.write_date = max(
                record.write_date or now, record.product_tmpl_id.write_date or now
            )

    def _compute_image_1920(self):
        """Get the image from the template if no image is set on the variant."""
        for record in self:
            record.image_1920 = record.image_variant_1920 or record.product_tmpl_id.image_1920

    def _set_image_1920(self):
        return self._set_template_field('image_1920', 'image_variant_1920')

    def _compute_image_1024(self):
        """Get the image from the template if no image is set on the variant."""
        for record in self:
            record.image_1024 = record.image_variant_1024 or record.product_tmpl_id.image_1024

    def _compute_image_512(self):
        """Get the image from the template if no image is set on the variant."""
        for record in self:
            record.image_512 = record.image_variant_512 or record.product_tmpl_id.image_512

    def _compute_image_256(self):
        """Get the image from the template if no image is set on the variant."""
        for record in self:
            record.image_256 = record.image_variant_256 or record.product_tmpl_id.image_256

    def _compute_image_128(self):
        """Get the image from the template if no image is set on the variant."""
        for record in self:
            record.image_128 = record.image_variant_128 or record.product_tmpl_id.image_128

    def _compute_can_image_1024_be_zoomed(self):
        """Get the image from the template if no image is set on the variant."""
        for record in self:
            record.can_image_1024_be_zoomed = record.can_image_variant_1024_be_zoomed if record.image_variant_1920 else record.product_tmpl_id.can_image_1024_be_zoomed

    def _get_placeholder_filename(self, field):
        image_fields = ['image_%s' % size for size in [1920, 1024, 512, 256, 128]]
        if field in image_fields:
            return self._get_product_placeholder_filename()
        return super()._get_placeholder_filename(field)

    def _get_product_placeholder_filename(self):
        return self.product_tmpl_id._get_product_placeholder_filename()

    def _get_barcodes_by_company(self):
        return [
            (company_id, [p.barcode for p in products if p.barcode])
            for company_id, products in groupby(self, lambda p: p.company_id.id)
        ]

    def _get_barcode_search_domain(self, barcodes_within_company, company_id):
        domain = [('barcode', 'in', barcodes_within_company)]
        if company_id:
            domain.append(('company_id', 'in', (False, company_id)))
        return domain

    def _check_duplicated_product_barcodes(self, barcodes_within_company, company_id):
        domain = self._get_barcode_search_domain(barcodes_within_company, company_id)
        products_by_barcode = self.sudo()._read_group(
            domain, ['barcode'], ['id:recordset'], having=[('__count', '>', 1)],
        )

        duplicates_as_str = "\n".join(
            self.env._(
                "- Barcode \"%(barcode)s\" already assigned to product(s): %(product_list)s",
                barcode=barcode, product_list=duplicate_products._filtered_access('read').mapped('display_name'),
            )
            for barcode, duplicate_products in products_by_barcode
        )
        if duplicates_as_str:
            duplicates_as_str += _(
                "\n\nNote: products that you don't have access to will not be shown above."
            )
            raise ValidationError(_("Barcode(s) already assigned:\n\n%s", duplicates_as_str))

    def _check_duplicated_packaging_barcodes(self, barcodes_within_company, company_id):
        packaging_domain = self._get_barcode_search_domain(barcodes_within_company, company_id)
        if self.env['product.uom'].sudo().search_count(packaging_domain, limit=1):
            raise ValidationError(_("A packaging already uses the barcode"))

    @api.constrains('barcode')
    def _check_barcode_uniqueness(self):
        """ With GS1 nomenclature, products and packagings use the same pattern. Therefore, we need
        to ensure the uniqueness between products' barcodes and packagings' ones"""
        # Barcodes should only be unique within a company
        self_ctx = self.with_context(skip_preprocess_gs1=True)
        for company_id, barcodes_within_company in self_ctx._get_barcodes_by_company():
            self_ctx._check_duplicated_product_barcodes(barcodes_within_company, company_id)
            self_ctx._check_duplicated_packaging_barcodes(barcodes_within_company, company_id)

    @api.constrains('company_id')
    def _check_company_id(self):
        combo_items = self.env['product.combo.item'].sudo().search([('product_id', 'in', self.ids)])
        combo_items._check_company(fnames=['product_id'])

    def _get_invoice_policy(self):
        return False

    @api.depends('product_template_attribute_value_ids')
    def _compute_combination_indices(self):
        for product in self:
            product.combination_indices = product.product_template_attribute_value_ids._ids2str()

    def _compute_is_product_variant(self):
        self.is_product_variant = True

    @api.onchange('lst_price')
    def _set_product_lst_price(self):
        for product in self:
            if self.env.context.get('uom'):
                value = self.env['uom.uom'].browse(self.env.context['uom'])._compute_price(product.lst_price, product.uom_id)
            else:
                value = product.lst_price
            value -= product.price_extra
            product.write({'list_price': value})

    @api.depends("product_template_attribute_value_ids.price_extra")
    def _compute_product_price_extra(self):
        for product in self:
            product.price_extra = sum(product.product_template_attribute_value_ids.mapped('price_extra'))

    @api.depends('list_price', 'price_extra')
    @api.depends_context('uom')
    def _compute_product_lst_price(self):
        to_uom = None
        if 'uom' in self.env.context:
            to_uom = self.env['uom.uom'].browse(self.env.context['uom'])

        for product in self:
            if to_uom:
                list_price = product.uom_id._compute_price(product.list_price, to_uom)
            else:
                list_price = product.list_price
            product.lst_price = list_price + product.price_extra

    @api.depends_context('partner_id')
    def _compute_product_code(self):
        read_access = self.env['ir.model.access'].check('product.supplierinfo', 'read', False)
        for product in self:
            product.code = product.default_code
            if read_access:
                for supplier_info in product.seller_ids:
                    if supplier_info.partner_id.id == product.env.context.get('partner_id'):
                        if supplier_info.product_id and supplier_info.product_id != product:
                            # Supplier info specific for another variant.
                            continue
                        product.code = supplier_info.product_code or product.default_code
                        if product == supplier_info.product_id:
                            # Supplier info specific for this variant.
                            break

    @api.depends_context('partner_id')
    def _compute_partner_ref(self):
        for product in self:
            for supplier_info in product.seller_ids:
                if supplier_info.partner_id.id == product.env.context.get('partner_id'):
                    product_name = supplier_info.product_name or product.default_code or product.name
                    product.partner_ref = '%s%s' % (product.code and '[%s] ' % product.code or '', product_name)
                    break
            else:
                product.partner_ref = product.display_name

    def _compute_product_document_count(self):
        for product in self:
            product.product_document_count = product.env['product.document'].search_count([
                ('res_model', '=', 'product.product'),
                ('res_id', 'in', product.ids),
            ])

    @api.depends('product_tag_ids', 'additional_product_tag_ids')
    def _compute_all_product_tag_ids(self):
        for product in self:
            product.all_product_tag_ids = (
                product.product_tag_ids | product.additional_product_tag_ids
            ).sorted('sequence')

    def _search_all_product_tag_ids(self, operator, operand):
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        return ['|', ('product_tag_ids', operator, operand), ('additional_product_tag_ids', operator, operand)]

    def _search_is_in_selected_section_of_order(self, operator, value):
        if operator != 'in':
            return NotImplemented
        ctx = self.env.context
        order_id = ctx.get('order_id')
        order_model = ctx.get('product_catalog_order_model')
        line_field = ctx.get('child_field')
        if not (order_id and order_model and line_field):
            return []

        product_ids = self.env[order_model].browse(order_id)[line_field].filtered(
            lambda line: line.get_parent_section_line().id == ctx.get('section_id'),
        ).mapped('product_id').ids

        return [('id', 'in', product_ids)]

    @api.onchange('standard_price')
    def _onchange_standard_price(self):
        if self.standard_price < 0:
            raise ValidationError(_("The cost of a product can't be negative."))

    @api.onchange('default_code')
    def _onchange_default_code(self):
        if not self.default_code:
            return

        domain = [('default_code', '=', self.default_code)]
        if self.id.origin:
            domain.append(('id', '!=', self.id.origin))

        if self.env['product.product'].search_count(domain, limit=1):
            return {'warning': {
                'title': _("Note:"),
                'message': _("The Reference '%s' already exists.", self.default_code),
            }}

    def _trigger_uom_warning(self):
        return False

    @api.onchange('uom_id')
    def _onchange_uom_id(self):
        if self._origin.uom_id == self.uom_id or not self._trigger_uom_warning():
            return
        message = _(
            'Changing the unit of measure for your product will apply a conversion 1 %(old_uom_name)s = 1 %(new_uom_name)s.\n'
            'All existing records (Sales orders, Purchase orders, etc.) using this product will be updated by replacing the unit name.',
            old_uom_name=self._origin.uom_id.display_name, new_uom_name=self.uom_id.display_name)
        return {
            'warning': {
                'title': _('What to expect ?'),
                'message': message,
            }
        }

    @api.model_create_multi
    def create(self, vals_list):
        products = super(ProductProduct, self.with_context(create_product_product=False)).create(vals_list)
        # `_get_variant_id_for_combination` depends on existing variants
        self.env.registry.clear_cache()
        return products

    def write(self, vals):
        res = super().write(vals)
        if 'product_template_attribute_value_ids' in vals:
            # `_get_variant_id_for_combination` depends on `product_template_attribute_value_ids`
            self.env.registry.clear_cache()
        elif 'active' in vals:
            # `_get_first_possible_variant_id` depends on variants active state
            self.env.registry.clear_cache()
        return res

    def action_archive(self):
        records = self.filtered('active')
        super().action_archive()
        # We deactivate product templates which are active with no active variants.
        records.product_tmpl_id.filtered(
            lambda product_tmpl: product_tmpl.active and not product_tmpl.product_variant_ids
        ).action_archive()

    def action_unarchive(self):
        records = self.filtered(lambda rec: not rec.active)
        super().action_unarchive()
        # We activate product templates which are inactive with active variants.
        records.product_tmpl_id.filtered(
            lambda product_tmpl: not product_tmpl.active and product_tmpl.product_variant_ids
        ).action_unarchive()

    def unlink(self):
        unlink_products_ids = set()
        unlink_templates_ids = set()

        # Check if products still exists, in case they've been unlinked by unlinking their template
        existing_products = self.exists()
        product_ids_by_template_id = {template.id: set(ids) for template, ids in self._read_group(
            domain=[('product_tmpl_id', 'in', existing_products.product_tmpl_id.ids)],
            groupby=['product_tmpl_id'],
            aggregates=['id:array_agg'],
        )}
        for product in existing_products:
            # If there is an image set on the variant and no image set on the
            # template, move the image to the template.
            if product.image_variant_1920 and not product.product_tmpl_id.image_1920:
                product.product_tmpl_id.image_1920 = product.image_variant_1920
            # Check if the product is last product of this template...
            has_other_products = product_ids_by_template_id.get(product.product_tmpl_id.id, set()) - {product.id}
            # ... and do not delete product template if it's configured to be created "on demand"
            if not has_other_products and not product.product_tmpl_id.has_dynamic_attributes():
                unlink_templates_ids.add(product.product_tmpl_id.id)
            unlink_products_ids.add(product.id)
        unlink_products = self.env['product.product'].browse(unlink_products_ids)
        res = super(ProductProduct, unlink_products).unlink()
        # delete templates after calling super, as deleting template could lead to deleting
        # products due to ondelete='cascade'
        unlink_templates = self.env['product.template'].browse(unlink_templates_ids)
        unlink_templates.unlink()
        # `_get_variant_id_for_combination` depends on existing variants
        self.env.registry.clear_cache()
        return res

    def _filter_to_unlink(self):
        return self

    def _unlink_or_archive(self, check_access=True):
        """Unlink or archive products.
        Try in batch as much as possible because it is much faster.
        Use dichotomy when an exception occurs.
        """

        # Avoid access errors in case the products is shared amongst companies
        # but the underlying objects are not. If unlink fails because of an
        # AccessError (e.g. while recomputing fields), the 'write' call will
        # fail as well for the same reason since the field has been set to
        # recompute.
        if check_access:
            self.check_access('unlink')
            self.check_access('write')
            self = self.sudo()
            to_unlink = self._filter_to_unlink()
            to_archive = self - to_unlink
            to_archive.write({'active': False})
            self = to_unlink

        try:
            with self.env.cr.savepoint(), tools.mute_logger('odoo.sql_db'):
                self.unlink()
        except Exception:
            # We catch all kind of exceptions to be sure that the operation
            # doesn't fail.
            if len(self) > 1:
                self[:len(self) // 2]._unlink_or_archive(check_access=False)
                self[len(self) // 2:]._unlink_or_archive(check_access=False)
            else:
                if self.active:
                    # Note: this can still fail if something is preventing
                    # from archiving.
                    # This is the case from existing stock reordering rules.
                    self.write({'active': False})

    def copy(self, default=None):
        """Variants are generated depending on the configuration of attributes
        and values on the template, so copying them does not make sense.

        For convenience the template is copied instead and its first variant is
        returned.
        """
        # copy variant is disabled in https://github.com/odoo/odoo/pull/38303
        # this returns the first possible combination of variant to make it
        # works for now, need to be fixed to return product_variant_id if it's
        # possible in the future

        # Use tmp recordset in case we copy several variants from the same template
        templates = [product.product_tmpl_id for product in self]
        templates_to_copy = self.env['product.template'].concat(*templates)
        new_templates = templates_to_copy.copy(default=default)
        new_products = self.env['product.product']
        for new_template in new_templates:
            new_products += new_template.product_variant_id or new_template._create_first_product_variant()
        return new_products

    @api.model
    def _search(self, domain, *args, **kwargs):
        # TDE FIXME: strange
        if self.env.context.get('search_default_categ_id'):
            domain = Domain(domain) & Domain('categ_id', 'child_of', self.env.context['search_default_categ_id'])
        return super()._search(domain, *args, **kwargs)

    @api.depends('name', 'default_code', 'product_tmpl_id')
    @api.depends_context('display_default_code', 'seller_id', 'company_id', 'partner_id', 'formatted_display_name', 'lang')
    def _compute_display_name(self):

        def get_display_name(name, code):
            if self.env.context.get('display_default_code', True) and code:
                if self.env.context.get('formatted_display_name'):
                    return f'{name}\t--{code}--'
                return f'[{code}] {name}'
            return name

        partner_id = self.env.context.get('partner_id')
        if partner_id:
            partner_ids = [partner_id, self.env['res.partner'].browse(partner_id).commercial_partner_id.id]
        else:
            partner_ids = []
        company_id = self.env.context.get('company_id')

        # all user don't have access to seller and partner
        # check access and use superuser
        self.check_access("read")

        product_template_ids = self.sudo().product_tmpl_id.ids

        if partner_ids:
            # prefetch the fields used by the `display_name`
            supplier_info = self.env['product.supplierinfo'].sudo().search_fetch(
                [('product_tmpl_id', 'in', product_template_ids), ('partner_id', 'in', partner_ids)],
                ['product_tmpl_id', 'product_id', 'company_id', 'product_name', 'product_code'],
            )
            supplier_info_by_template = {}
            for r in supplier_info:
                supplier_info_by_template.setdefault(r.product_tmpl_id, []).append(r)

        for product in self.sudo():
            variant = product.product_template_attribute_value_ids._get_combination_name()

            name = variant and "%s (%s)" % (product.name, variant) or product.name
            sellers = self.env['product.supplierinfo'].sudo().browse(self.env.context.get('seller_id')) or []
            if not sellers and partner_ids:
                product_supplier_info = supplier_info_by_template.get(product.product_tmpl_id, [])
                sellers = [x for x in product_supplier_info if x.product_id and x.product_id == product]
                if not sellers:
                    sellers = [x for x in product_supplier_info if not x.product_id]
                # Filter out sellers based on the company. This is done afterwards for a better
                # code readability. At this point, only a few sellers should remain, so it should
                # not be a performance issue.
                if company_id:
                    sellers = [x for x in sellers if x.company_id.id in [company_id, False]]
            if sellers:
                temp = []
                for s in sellers:
                    seller_variant = s.product_name and (
                        variant and "%s (%s)" % (s.product_name, variant) or s.product_name
                        ) or False
                    temp.append(get_display_name(seller_variant or name, s.product_code or product.default_code))

                # => Feature drop here, one record can only have one display_name now, instead separate with `,`
                # Remove this comment
                product.display_name = ", ".join(unique(temp))
            else:
                product.display_name = get_display_name(name, product.default_code)

    @api.model
    def _search_display_name(self, operator, value):
        is_positive = operator not in Domain.NEGATIVE_OPERATORS
        template_domains = [[('name', operator, value)]]
        product_domains = [[('default_code', operator, value)]]

        if operator == 'in':
            product_domains.append([('barcode', 'in', value)])
            for v in value:
                if isinstance(v, str) and (m := re.search(r'(\[(.*?)\])', v)):
                    product_domains.append([('default_code', '=', m.group(2))])
        elif operator.endswith('like') and is_positive:
            product_domains.append([('barcode', 'in', [value])])

        supplier_domain = []
        if partner_id := self.env.context.get('partner_id'):
            supplier_domain = [
                ('partner_id', '=', partner_id),
                '|',
                ('product_code', operator, value),
                ('product_name', operator, value),
            ]

        # AND clauses properly hit indexes so no need for custom sql in this case.
        if operator in Domain.NEGATIVE_OPERATORS:
            domains = template_domains + product_domains
            if supplier_domain:
                domains.append([('product_tmpl_id.seller_ids', 'any', supplier_domain)])
            return Domain.AND(domains)

        # Disable active_test to simplify subqueries
        self_no_active_test = self.with_context(active_test=False)
        queries = [
            self_no_active_test._search([
                ('product_tmpl_id', 'in', self_no_active_test.env['product.template']._search(Domain.OR(template_domains)))
            ]),
            self_no_active_test._search(Domain.OR(product_domains)),
        ]
        if supplier_domain:
            queries.append(
                self_no_active_test._search([
                    (
                        'product_tmpl_id',
                        'in',
                        self_no_active_test.env['product.supplierinfo']._search(supplier_domain).subselect('product_tmpl_id'),
                    )
                ])
            )
        query = SQL(
            """(%s)""",
            SQL("UNION ALL").join(
                [SQL("(%s)", query.select()) for query in queries]
            )
        )

        return [('id', 'in', query)]

    @api.model
    def name_search(self, name='', domain=None, operator='ilike', limit=100):
        if not name:
            return super().name_search(name, domain, operator, limit)
        # search progressively by the most specific attributes
        positive_operators = ['=', 'ilike', '=ilike', 'like', '=like']
        is_positive = not operator in Domain.NEGATIVE_OPERATORS
        products = self.browse()
        domain = Domain(domain or Domain.TRUE)
        if operator in positive_operators:
            products = self.search_fetch(domain & Domain('default_code', '=', name), ['display_name'], limit=limit) \
                or self.search_fetch(domain & Domain('barcode', '=', name), ['display_name'], limit=limit)
        if not products:
            if is_positive:
                # Do not merge the 2 next lines into one single search, SQL search performance would be abysmal
                # on a database with thousands of matching products, due to the huge merge+unique needed for the
                # OR operator (and given the fact that the 'name' lookup results come from the ir.translation table
                # Performing a quick memory merge of ids in Python will give much better performance
                products = self.search_fetch(domain & Domain('default_code', operator, name), ['display_name'], limit=limit)
                limit_rest = limit and limit - len(products)
                if limit_rest is None or limit_rest > 0:
                    products_query = self._search(domain & Domain('default_code', operator, name), limit=limit)
                    products |= self.search_fetch(domain & Domain('id', 'not in', products_query) & Domain('name', operator, name), ['display_name'], limit=limit_rest)
            else:
                domain_neg = Domain('name', operator, name) & (
                    Domain('default_code', operator, name) | Domain('default_code', '=', False)
                )
                products = self.search_fetch(domain & domain_neg, ['display_name'], limit=limit)
        if not products and operator in positive_operators and (m := re.search(r'(\[(.*?)\])', name)):
            match_domain = Domain('default_code', '=', m.group(2))
            products = self.search_fetch(domain & match_domain, ['display_name'], limit=limit)
        if not products and (partner_id := self.env.context.get('partner_id')):
            # still no results, partner in context: search on supplier info as last hope to find something
            supplier_domain = Domain([
                ('partner_id', '=', partner_id),
                '|',
                ('product_code', operator, name),
                ('product_name', operator, name),
            ])
            match_domain = Domain('product_tmpl_id.seller_ids', 'any', supplier_domain)
            products = self.search_fetch(domain & match_domain, ['display_name'], limit=limit)
        return [(product.id, product.display_name) for product in products.sudo()]

    @api.model
    def view_header_get(self, view_id, view_type):
        if self.env.context.get('categ_id'):
            return _(
                'Products: %(category)s',
                category=self.env['product.category'].browse(self.env.context['categ_id']).name,
            )
        return super().view_header_get(view_id, view_type)

    #=== ACTION METHODS ===#

    @api.readonly
    def action_open_label_layout(self):
        if any(product.type == 'service' for product in self):
            raise ValidationError(_('Labels cannot be printed for products of service type'))
        action = self.env['ir.actions.act_window']._for_xml_id('product.action_open_label_layout')
        action['context'] = {'default_product_ids': self.ids}
        return action

    def open_product_template(self):
        """ Utility method used to add an "Open Template" button in product views """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'view_mode': 'form',
            'res_id': self.product_tmpl_id.id,
            'target': 'new'
        }

    @api.readonly
    def action_open_documents(self):
        res = self.product_tmpl_id.action_open_documents()
        res['context'].update({
            'default_res_model': self._name,
            'default_res_id': self.id,
            'search_default_context_variant': True,
        })
        return res

    #=== BUSINESS METHODS ===#

    def _prepare_sellers(self, params=False):
        sellers = self.seller_ids._get_filtered_supplier(self.env.company, self, params)
        return sellers.sorted(lambda s: (s.sequence, -s.min_qty, s.price, s.id))

    def _get_filtered_sellers(self, partner_id=False, quantity=0.0, date=None, uom_id=False, params=False):
        self.ensure_one()
        if not date:
            date = fields.Date.context_today(self)
        precision = self.env['decimal.precision'].precision_get('Product Unit')

        sellers_filtered = self._prepare_sellers(params)
        sellers = self.env['product.supplierinfo']
        for seller in sellers_filtered:
            # Set quantity in UoM of seller
            quantity_uom_seller = quantity
            if quantity_uom_seller and uom_id and uom_id != seller.product_uom_id:
                quantity_uom_seller = uom_id._compute_quantity(quantity_uom_seller, seller.product_uom_id)

            if seller.date_start and seller.date_start > date:
                continue
            if seller.date_end and seller.date_end < date:
                continue
            if params and params.get('force_uom') and seller.product_uom_id != uom_id and seller.product_uom_id != self.uom_id:
                continue
            if partner_id and seller.partner_id not in [partner_id, partner_id.parent_id]:
                continue
            if quantity is not None and float_compare(quantity_uom_seller, seller.min_qty, precision_digits=precision) == -1:
                continue
            if seller.product_id and seller.product_id != self:
                continue
            sellers |= seller
        return sellers

    def _select_seller(self, partner_id=False, quantity=0.0, date=None, uom_id=False, ordered_by='price_discounted', params=False):
        # Always sort by discounted price but another field can take the primacy through the `ordered_by` param.
        sort_key = ('price_discounted', 'sequence', 'id')
        if ordered_by != 'price_discounted':
            sort_key = (ordered_by, 'price_discounted', 'sequence', 'id')

        def sort_function(record):
            vals = {
                'price_discounted': record.currency_id._convert(
                    record.price_discounted,
                    record.env.company.currency_id,
                    record.env.company,
                    date or fields.Date.context_today(self),
                    round=False,
                ),
            }
            return [vals.get(key, record[key]) for key in sort_key]
        sellers = self._get_filtered_sellers(partner_id=partner_id, quantity=quantity, date=date, uom_id=uom_id, params=params)
        res = self.env['product.supplierinfo']
        for seller in sellers:
            if not res or res.partner_id == seller.partner_id:
                res |= seller
        return res and res.sorted(sort_function)[:1]

    def _get_product_price_context(self, combination):
        self.ensure_one()
        res = {}

        no_variant_attributes_price_extra = self._get_no_variant_attributes_price_extra(combination)

        if no_variant_attributes_price_extra:
            res['no_variant_attributes_price_extra'] = no_variant_attributes_price_extra

        return res

    def _get_no_variant_attributes_price_extra(self, combination):
        # It is possible that a no_variant attribute is still in a variant if
        # the type of the attribute has been changed after creation.
        return sum(
            ptav.price_extra for ptav in combination.filtered(
                lambda ptav:
                    ptav.price_extra
                    and ptav.product_tmpl_id == self.product_tmpl_id
                    and ptav not in self.product_template_attribute_value_ids
            )
        )

    def _get_attributes_extra_price(self):
        self.ensure_one()

        return self.price_extra + self.env.context.get('no_variant_attributes_price_extra', 0)

    def _price_compute(self, price_type, uom=None, currency=None, company=None, date=False):
        company = company or self.env.company
        date = date or fields.Date.context_today(self)

        self = self.with_company(company)
        if price_type == 'standard_price':
            # standard_price field can only be seen by users in base.group_user
            # Thus, in order to compute the sale price from the cost for users not in this group
            # We fetch the standard price as the superuser
            self = self.sudo()

        prices = dict.fromkeys(self.ids, 0.0)
        for product in self:
            price = product[price_type] or 0.0
            price_currency = product.currency_id
            if price_type == 'standard_price':
                price_currency = product.cost_currency_id
            elif price_type == 'list_price':
                price += product._get_attributes_extra_price()

            if uom:
                price = product.uom_id._compute_price(price, uom)

            # Convert from current user company currency to asked one
            # This is right cause a field cannot be in more than one currency
            if currency:
                price = price_currency._convert(price, currency, company, date)

            prices[product.id] = price

        return prices

    @api.model
    def get_empty_list_help(self, help_message):
        self = self.with_context(
            empty_list_help_document_name=_("product"),
        )
        return super(ProductProduct, self).get_empty_list_help(help_message)

    def get_product_multiline_description_sale(self):
        """ Compute a multiline description of this product, in the context of sales
        (do not use for purchases or other display reasons that don't intend to use "description_sale").
        It will often be used as the default description of a sale order line referencing this product.
        """
        name = self.display_name
        if self.description_sale:
            name += '\n' + self.description_sale

        return name

    def _is_variant_possible(self, parent_combination=None):
        """Return whether the variant is possible based on its own combination,
        and optionally a parent combination.

        See `_is_combination_possible` for more information.

        :param parent_combination: combination from which `self` is an
            optional or accessory product.
        :type parent_combination: recordset `product.template.attribute.value`

        :return: ẁhether the variant is possible based on its own combination
        :rtype: bool
        """
        self.ensure_one()
        return self.product_tmpl_id._is_combination_possible(self.product_template_attribute_value_ids, parent_combination=parent_combination, ignore_no_variant=True)

    def get_contextual_price(self):
        return self._get_contextual_price()

    def _get_contextual_price(self):
        # FIXME VFE this won't consider ptavs extra prices, since we rely on the template price
        self.ensure_one()
        return self.product_tmpl_id._get_contextual_price(self)

    def _get_contextual_discount(self):
        self.ensure_one()

        pricelist = self.product_tmpl_id._get_contextual_pricelist()
        if not pricelist:
            # No pricelist = no discount
            return 0.0

        lst_price = self.currency_id._convert(
            self.lst_price,
            pricelist.currency_id,
            self.env.company,
            fields.Datetime.now(),
            round=False
        )
        if lst_price:
            return (lst_price - self._get_contextual_price()) / lst_price
        return 0.0

    def _update_uom(self, to_uom_id):
        """ Hook to handle an UoM modification. Avoid recomputation and just replace the
        many2one field on the impacted models."""
        return True
