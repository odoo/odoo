# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools
import logging

from collections import defaultdict

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools.image import is_image_size_above

_logger = logging.getLogger(__name__)
PRICE_CONTEXT_KEYS = ['pricelist', 'quantity', 'uom', 'date']


class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _description = "Product"
    _order = "is_favorite desc, name"
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'uom_id' in fields_list and not res.get('uom_id'):
            res['uom_id'] = self._get_default_uom_id().id
        return res

    @tools.ormcache()
    def _get_default_uom_id(self):
        # Deletion forbidden (at least through unlink)
        return self.env.ref('uom.product_uom_unit')

    def _read_group_categ_id(self, categories, domain):
        category_ids = self.env.context.get('default_categ_id')
        if not category_ids and self.env.context.get('group_expand'):
            category_ids = categories.sudo()._search([], order=categories._order)
        return categories.browse(category_ids)

    name = fields.Char('Name', index='trigram', required=True, translate=True)
    sequence = fields.Integer('Sequence', default=1, help='Gives the sequence order when displaying a product list')
    description = fields.Html(
        'Description', translate=True)
    description_purchase = fields.Text(
        'Purchase Description', translate=True)
    description_sale = fields.Text(
        'Sales Description', translate=True,
        help="A description of the Product that you want to communicate to your customers. "
             "This description will be copied to every Sales Order, Delivery Order and Customer Invoice/Credit Note")
    type = fields.Selection(
        string="Product Type",
        help="Goods are tangible materials and merchandise you provide.\n"
             "A service is a non-material product you provide.",
        selection=[
            ('consu', "Goods"),
            ('service', "Service"),
            ('combo', "Combo"),
        ],
        required=True,
        default='consu',
    )
    combo_ids = fields.Many2many(
        string="Combo Choices", comodel_name='product.combo', check_company=True
    )
    service_tracking = fields.Selection(selection=[
            ('no', 'Nothing'),
        ],
        string="Create on Order",
        default="no",
        compute="_compute_service_tracking",
        required=True,
        store=True,
        readonly=False,
    )
    categ_id = fields.Many2one(
        string="Product Category",
        comodel_name='product.category',
        group_expand='_read_group_categ_id',
        tracking=True,
    )

    currency_id = fields.Many2one(
        'res.currency', 'Currency', compute='_compute_currency_id')
    cost_currency_id = fields.Many2one(
        'res.currency', 'Cost Currency', compute='_compute_cost_currency_id')

    # list_price: catalog price, user defined
    list_price = fields.Float(
        'Sales Price', default=1.0,
        digits='Product Price',
        tracking=True,
        help="Price at which the product is sold to customers.",
    )
    standard_price = fields.Float(
        'Cost', compute='_compute_standard_price',
        inverse='_set_standard_price', search='_search_standard_price',
        digits='Product Price', groups="base.group_user",
        help="""Value of the product (automatically computed in AVCO).
        Used to value the product when the purchase cost is not known (e.g. inventory adjustment).
        Used to compute margins on sale orders.""")

    volume = fields.Float(
        'Volume', compute='_compute_volume', inverse='_set_volume', digits='Volume', store=True)
    volume_uom_name = fields.Char(string='Volume unit of measure label', compute='_compute_volume_uom_name')
    weight = fields.Float(
        'Weight', compute='_compute_weight', digits='Stock Weight',
        inverse='_set_weight', store=True)
    weight_uom_name = fields.Char(string='Weight unit of measure label', compute='_compute_weight_uom_name')

    sale_ok = fields.Boolean('Sales', default=True)
    purchase_ok = fields.Boolean('Purchase', default=True, compute='_compute_purchase_ok', store=True, readonly=False)
    uom_id = fields.Many2one(
        'uom.uom', 'Unit of Measure',
        default=_get_default_uom_id, required=True,
        help="Default unit of measure used for all stock operations.")
    uom_name = fields.Char(string='Unit of Measure Name', related='uom_id.name', readonly=True)
    uom_po_id = fields.Many2one(
        'uom.uom', 'Purchase Unit',
        compute='_compute_uom_po_id', required=True, readonly=False, store=True, precompute=True,
        help="Default unit of measure used for purchase orders. It must be in the same category as the default unit of measure.")
    uom_ids = fields.Many2many('uom.uom', string='Packagings', help="Packagings which can be used for sales")
    company_id = fields.Many2one(
        'res.company', 'Company', index=True)
    seller_ids = fields.One2many('product.supplierinfo', 'product_tmpl_id', 'Vendors', depends_context=('company',))
    variant_seller_ids = fields.One2many('product.supplierinfo', 'product_tmpl_id')

    active = fields.Boolean('Active', default=True, help="If unchecked, it will allow you to hide the product without removing it.")
    color = fields.Integer('Color Index')

    is_product_variant = fields.Boolean(string='Is a product variant', compute='_compute_is_product_variant')
    attribute_line_ids = fields.One2many('product.template.attribute.line', 'product_tmpl_id', 'Product Attributes', copy=True)

    valid_product_template_attribute_line_ids = fields.Many2many('product.template.attribute.line',
        compute="_compute_valid_product_template_attribute_line_ids", string='Valid Product Attribute Lines')

    product_variant_ids = fields.One2many('product.product', 'product_tmpl_id', 'Products', required=True)
    # performance: product_variant_id provides prefetching on the first product variant only
    product_variant_id = fields.Many2one('product.product', 'Product', compute='_compute_product_variant_id')

    product_variant_count = fields.Integer(
        '# Product Variants', compute='_compute_product_variant_count')

    # related to display product product information if is_product_variant
    barcode = fields.Char('Barcode', compute='_compute_barcode', inverse='_set_barcode', search='_search_barcode')
    default_code = fields.Char(
        'Internal Reference', compute='_compute_default_code',
        inverse='_set_default_code', store=True)

    pricelist_item_count = fields.Integer("Number of price rules", compute="_compute_item_count")

    product_document_ids = fields.One2many(
        string="Documents",
        comodel_name='product.document',
        inverse_name='res_id',
        domain=lambda self: [('res_model', '=', self._name)])
    product_document_count = fields.Integer(
        string="Documents Count", compute='_compute_product_document_count')

    can_image_1024_be_zoomed = fields.Boolean("Can Image 1024 be zoomed", compute='_compute_can_image_1024_be_zoomed', store=True)
    has_configurable_attributes = fields.Boolean("Is a configurable product", compute='_compute_has_configurable_attributes', store=True)

    is_dynamically_created = fields.Boolean("Is Dynamically Created", compute='_compute_is_dynamically_created')

    product_tooltip = fields.Char(compute='_compute_product_tooltip')

    is_favorite = fields.Boolean(string="Favorite")
    _is_favorite_index = models.Index("(is_favorite) WHERE is_favorite IS TRUE")

    product_tag_ids = fields.Many2many(
        string="Tags", comodel_name='product.tag', relation='product_tag_product_template_rel'
    )
    # Properties
    product_properties = fields.Properties('Properties', definition='categ_id.product_properties_definition', copy=True)

    @api.depends('type')
    def _compute_service_tracking(self):
        self.filtered(lambda product: product.type != 'service').service_tracking = 'no'

    def _compute_purchase_ok(self):
        pass

    @api.depends('uom_id')
    def _compute_uom_po_id(self):
        for template in self:
            if not template.uom_po_id or template.uom_id.category_id != template.uom_po_id.category_id:
                template.uom_po_id = template.uom_id

    def _compute_item_count(self):
        for template in self:
            # Pricelist item count counts the rules applicable on current template or on its variants.
            template.pricelist_item_count = template.env['product.pricelist.item'].search_count([
                '&',
                '|', ('product_tmpl_id', '=', template.id), ('product_id', 'in', template.product_variant_ids.ids),
                ('pricelist_id.active', '=', True),
                ('compute_price', '=', 'fixed'),
            ])

    def _compute_product_document_count(self):
        for template in self:
            template.product_document_count = template.env['product.document'].search_count([
                '|',
                    '&', ('res_model', '=', 'product.template'), ('res_id', '=', template.id),
                    '&',
                        ('res_model', '=', 'product.product'),
                        ('res_id', 'in', template.product_variant_ids.ids),
            ])

    @api.depends('image_1920', 'image_1024')
    def _compute_can_image_1024_be_zoomed(self):
        for template in self.with_context(bin_size=False):
            template.can_image_1024_be_zoomed = template.image_1920 and is_image_size_above(template.image_1920, template.image_1024)

    @api.depends(
        'attribute_line_ids',
        'attribute_line_ids.value_ids',
        'attribute_line_ids.attribute_id.create_variant',
        'attribute_line_ids.attribute_id.display_type',
        'attribute_line_ids.value_ids.is_custom',
    )
    def _compute_has_configurable_attributes(self):
        """A product is considered configurable if:
        - It has dynamic attributes
        - It has any attribute line with at least 2 attribute values configured
        - It has multi-checkbox display type
        - It has at least one custom attribute value
        """
        for product in self:
            product.has_configurable_attributes = (
                product.has_dynamic_attributes() or any(
                    ptal._is_configurable()
                    for ptal in product.attribute_line_ids
                )
            )

    @api.depends('attribute_line_ids.attribute_id')
    def _compute_is_dynamically_created(self):
        for template in self:
            template.is_dynamically_created = any(
                line.attribute_id.create_variant == 'dynamic'
                for line in template.attribute_line_ids
            )

    @api.depends('product_variant_ids')
    def _compute_product_variant_id(self):
        for p in self:
            p.product_variant_id = p.product_variant_ids[:1].id

    @api.constrains('company_id')
    def _check_barcode_uniqueness(self):
        for template in self:
            template.product_variant_ids._check_barcode_uniqueness()

    @api.depends('company_id')
    def _compute_currency_id(self):
        main_company = self.env['res.company']._get_main_company()
        for template in self:
            template.currency_id = template.company_id.sudo().currency_id.id or main_company.currency_id.id

    @api.depends('company_id')
    @api.depends_context('company')
    def _compute_cost_currency_id(self):
        env_currency_id = self.env.company.currency_id.id
        for template in self:
            template.cost_currency_id = template.company_id.currency_id.id or env_currency_id

    def _compute_template_field_from_variant_field(self, fname, default=False):
        """Sets the value of the given field based on the template variant values

        Equals to product_variant_ids[fname] if it's a single variant product.
        Otherwise, sets the value specified in ``default``.
        It's used to compute fields like barcode, weight, volume..

        :param str fname: name of the field to compute
            (field name must be identical between product.product & product.template models)
        :param default: default value to set when there are multiple or no variants on the template
        :return: None
        """
        for template in self:
            variant_count = len(template.product_variant_ids)
            if variant_count == 1:
                template[fname] = template.product_variant_ids[fname]
            elif variant_count == 0 and self.env.context.get("active_test", True):
                # If the product has no active variants, retry without the active_test
                template_ctx = template.with_context(active_test=False)
                template_ctx._compute_template_field_from_variant_field(fname, default=default)
            else:
                template[fname] = default

    def _set_product_variant_field(self, fname):
        """Propagate the value of the given field from the templates to their unique variant.

        Only if it's a single variant product.
        It's used to set fields like barcode, weight, volume..

        :param str fname: name of the field whose value should be propagated to the variant.
            (field name must be identical between product.product & product.template models)
        """
        for template in self:
            count = len(template.product_variant_ids)
            if count == 1:
                template.product_variant_ids[fname] = template[fname]
            elif count == 0:
                archived_variants = self.with_context(active_test=False).product_variant_ids
                if len(archived_variants) == 1:
                    archived_variants[fname] = template[fname]

    @api.depends_context('company')
    @api.depends('product_variant_ids.standard_price')
    def _compute_standard_price(self):
        # Depends on force_company context because standard_price is company_dependent
        # on the product_product
        self._compute_template_field_from_variant_field('standard_price')

    def _set_standard_price(self):
        self._set_product_variant_field('standard_price')

    def _search_standard_price(self, operator, value):
        return [('product_variant_ids.standard_price', operator, value)]

    @api.depends('product_variant_ids.volume')
    def _compute_volume(self):
        self._compute_template_field_from_variant_field('volume')

    def _set_volume(self):
        self._set_product_variant_field('volume')

    @api.depends('product_variant_ids.weight')
    def _compute_weight(self):
        self._compute_template_field_from_variant_field('weight')

    def _set_weight(self):
        self._set_product_variant_field('weight')

    def _compute_is_product_variant(self):
        self.is_product_variant = False

    @api.depends('product_variant_ids.barcode')
    def _compute_barcode(self):
        self._compute_template_field_from_variant_field('barcode')

    def _search_barcode(self, operator, value):
        subquery = self.with_context(active_test=False)._search([
            ('product_variant_ids.barcode', operator, value),
        ])
        return [('id', 'in', subquery)]

    def _set_barcode(self):
        self._set_product_variant_field('barcode')

    @api.model
    def _get_weight_uom_id_from_ir_config_parameter(self):
        """ Get the unit of measure to interpret the `weight` field. By default, we considerer
        that weights are expressed in kilograms. Users can configure to express them in pounds
        by adding an ir.config_parameter record with "product.product_weight_in_lbs" as key
        and "1" as value.
        """
        product_weight_in_lbs_param = self.env['ir.config_parameter'].sudo().get_param('product.weight_in_lbs')
        if product_weight_in_lbs_param == '1':
            return self.env.ref('uom.product_uom_lb')
        else:
            return self.env.ref('uom.product_uom_kgm')

    @api.model
    def _get_length_uom_id_from_ir_config_parameter(self):
        """ Get the unit of measure to interpret the `length`, 'width', 'height' field.
        By default, we considerer that length are expressed in millimeters. Users can configure
        to express them in feet by adding an ir.config_parameter record with "product.volume_in_cubic_feet"
        as key and "1" as value.
        """
        product_length_in_feet_param = self.env['ir.config_parameter'].sudo().get_param('product.volume_in_cubic_feet')
        if product_length_in_feet_param == '1':
            return self.env.ref('uom.product_uom_foot')
        else:
            return self.env.ref('uom.product_uom_millimeter')

    @api.model
    def _get_volume_uom_id_from_ir_config_parameter(self):
        """ Get the unit of measure to interpret the `volume` field. By default, we consider
        that volumes are expressed in cubic meters. Users can configure to express them in cubic feet
        by adding an ir.config_parameter record with "product.volume_in_cubic_feet" as key
        and "1" as value.
        """
        product_length_in_feet_param = self.env['ir.config_parameter'].sudo().get_param('product.volume_in_cubic_feet')
        if product_length_in_feet_param == '1':
            return self.env.ref('uom.product_uom_cubic_foot')
        else:
            return self.env.ref('uom.product_uom_cubic_meter')

    @api.model
    def _get_weight_uom_name_from_ir_config_parameter(self):
        return self._get_weight_uom_id_from_ir_config_parameter().display_name

    @api.model
    def _get_length_uom_name_from_ir_config_parameter(self):
        return self._get_length_uom_id_from_ir_config_parameter().display_name

    @api.model
    def _get_volume_uom_name_from_ir_config_parameter(self):
        return self._get_volume_uom_id_from_ir_config_parameter().display_name

    @api.depends('type')
    def _compute_weight_uom_name(self):
        self.weight_uom_name = self._get_weight_uom_name_from_ir_config_parameter()

    @api.depends('type')
    def _compute_volume_uom_name(self):
        self.volume_uom_name = self._get_volume_uom_name_from_ir_config_parameter()

    @api.depends('product_variant_ids.product_tmpl_id')
    def _compute_product_variant_count(self):
        for template in self:
            template.product_variant_count = len(template.product_variant_ids)

    @api.onchange('default_code')
    def _onchange_default_code(self):
        if not self.default_code:
            return

        domain = [('default_code', '=', self.default_code)]
        if self.id.origin:
            domain.append(('id', '!=', self.id.origin))

        if self.env['product.template'].search_count(domain, limit=1):
            return {'warning': {
                'title': _("Note:"),
                'message': _("The Internal Reference '%s' already exists.", self.default_code),
            }}

    @api.depends('product_variant_ids.default_code')
    def _compute_default_code(self):
        self._compute_template_field_from_variant_field('default_code')

    def _set_default_code(self):
        self._set_product_variant_field('default_code')

    @api.depends('type')
    def _compute_product_tooltip(self):
        self.product_tooltip = False
        for template in self:
            template.product_tooltip = template._prepare_tooltip()

    def _prepare_tooltip(self):
        self.ensure_one()
        tooltip = ""
        if self.type == 'combo':
            tooltip = _(
                "Combos allow to choose one product amongst a selection of choices per category."
            )
        return tooltip

    @api.onchange('uom_id')
    def _onchange_uom_id(self):
        if self.uom_id:
            self.uom_po_id = self.uom_id.id

    @api.onchange('type')
    def _onchange_type(self):
        if self.type == 'combo':
            if self.attribute_line_ids:
                raise UserError(_("Combo products can't have attributes."))
            combo_items = self.env['product.combo.item'].sudo().search([
                ('product_id', 'in', self.product_variant_ids.ids)
            ])
            if combo_items:
                raise UserError(_(
                    "This product is part of a combo, so its type can't be changed to \"combo\"."
                ))
            self.purchase_ok = False
        return {}

    @api.constrains('type', 'combo_ids')
    def _check_combo_ids_not_empty(self):
        for template in self:
            if template.type == 'combo' and not template.combo_ids:
                raise ValidationError(_("A combo product must contain at least 1 combo choice."))

    @api.constrains('type', 'combo_ids', 'sale_ok')
    def _check_sale_combo_ids(self):
        for template in self:
            if (
                template.type == 'combo'
                and template.sale_ok
                and any(
                    not product.sale_ok for product in template.combo_ids.combo_item_ids.product_id
                )
            ):
                raise ValidationError(
                    _("A sellable combo product can only contain sellable products.")
                )

    def _get_related_fields_variant_template(self):
        """ Return a list of fields present on template and variants models and that are related"""
        return ['barcode', 'default_code', 'standard_price', 'volume', 'weight', 'product_properties']

    @api.model_create_multi
    def create(self, vals_list):
        ''' Store the initial standard price in order to be able to retrieve the cost of a product template for a given date'''
        templates = super(ProductTemplate, self).create(vals_list)
        if self._context.get("create_product_product", True):
            templates._create_variant_ids()

        # This is needed to set given values to first variant after creation
        for template, vals in zip(templates, vals_list):
            related_vals = {}
            for field_name in self._get_related_fields_variant_template():
                if vals.get(field_name):
                    related_vals[field_name] = vals[field_name]
            if related_vals:
                template.write(related_vals)

        return templates

    def write(self, vals):
        res = super(ProductTemplate, self).write(vals)
        if self._context.get("create_product_product", True) and 'attribute_line_ids' in vals or (vals.get('active') and len(self.product_variant_ids) == 0):
            self._create_variant_ids()
        if 'active' in vals and not vals.get('active'):
            self.with_context(active_test=False).mapped('product_variant_ids').write({'active': vals.get('active')})
        if 'image_1920' in vals:
            self.env['product.product'].invalidate_model([
                'image_1920',
                'image_1024',
                'image_512',
                'image_256',
                'image_128',
                'can_image_1024_be_zoomed',
            ])
        return res

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        if 'name' not in default:
            for template, vals in zip(self, vals_list):
                vals['name'] = _("%s (copy)", template.name)
        return vals_list

    def copy(self, default=None):
        res = super().copy(default=default)
        # Since we don't copy the product template attribute values, we need to match the extra prices.
        for ptal, copied_ptal in zip(self.attribute_line_ids, res.attribute_line_ids):
            for ptav, copied_ptav in zip(ptal.product_template_value_ids, copied_ptal.product_template_value_ids):
                if not ptav.price_extra:
                    continue
                # security check
                if ptav.attribute_id == copied_ptav.attribute_id and ptav.product_attribute_value_id == copied_ptav.product_attribute_value_id:
                    copied_ptav.price_extra = ptav.price_extra
        return res

    @api.depends('name', 'default_code')
    def _compute_display_name(self):
        for template in self:
            template.display_name = False if not template.name else (
                '{}{}'.format(
                    template.default_code and '[%s] ' % template.default_code or '', template.name
                ))

    @api.model
    def _search_display_name(self, operator, value):
        domain = super()._search_display_name(operator, value)
        if self.env.context.get('search_product_product', bool(value)):
            combine = expression.OR if operator not in expression.NEGATIVE_TERM_OPERATORS else expression.AND
            domain = combine([domain, [('product_variant_ids', operator, value)]])
        return domain

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        # Only use the product.product heuristics if there is a search term and the domain
        # does not specify a match on `product.template` IDs.
        self_obj = self
        if 'search_product_product' not in self.env.context and any(term[0] == 'id' for term in (args or [])):
            self_obj = self_obj.with_context(search_product_product=False)
        return super(ProductTemplate, self_obj).name_search(name, args, operator, limit)

    #=== ACTION METHODS ===#

    def action_open_label_layout(self):
        action = self.env['ir.actions.act_window']._for_xml_id('product.action_open_label_layout')
        action['context'] = {'default_product_tmpl_ids': self.ids}
        return action

    def open_pricelist_rules(self):
        self.ensure_one()
        domain = ['|',
            ('product_tmpl_id', '=', self.id),
            ('product_id', 'in', self.product_variant_ids.ids),
            ('compute_price', '=', 'fixed'),
        ]
        return {
            'name': _('Price Rules'),
            'view_mode': 'list,form',
            'views': [(self.env.ref('product.product_pricelist_item_tree_view_from_product').id, 'list')],
            'res_model': 'product.pricelist.item',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': domain,
            'context': {
                'default_product_tmpl_id': self.id,
                'default_applied_on': '1_product',
                'product_without_variants': self.product_variant_count == 1,
                'search_default_visible': True,
            },
        }

    @api.readonly
    def action_open_documents(self):
        self.ensure_one()
        return {
            'name': _('Documents'),
            'type': 'ir.actions.act_window',
            'res_model': 'product.document',
            'view_mode': 'kanban,list,form',
            'context': {
                'default_res_model': self._name,
                'default_res_id': self.id,
                'default_company_id': self.company_id.id,
            },
            'domain': [
                '|',
                    '&', ('res_model', '=', 'product.template'), ('res_id', '=', self.id),
                    '&',
                        ('res_model', '=', 'product.product'),
                        ('res_id', 'in', self.product_variant_ids.ids),
            ],
            'target': 'current',
            'help': """
                <p class="o_view_nocontent_smiling_face">
                    %s
                </p>
                <p>
                    %s
                    <br/>
                    %s
                </p>
                <p>
                    <a class="oe_link" href="https://www.odoo.com/documentation/18.0/_downloads/5f0840ed187116c425fdac2ab4b592e1/pdfquotebuilderexamples.zip">
                    %s
                    </a>
                </p>
            """ % (
                _("Upload files to your product"),
                _("Use this feature to store any files you would like to share with your customers"),
                _("(e.g: product description, ebook, legal notice, ...)."),
                _("Download examples")
            )
        }

    #=== BUSINESS METHODS ===#

    def _get_product_price_context(self, combination):
        self.ensure_one()
        res = {}

        current_attributes_price_extra = [
            ptav.price_extra for ptav in combination.filtered(
                lambda ptav:
                    ptav.price_extra
                    and ptav.product_tmpl_id == self
            )
        ]
        if current_attributes_price_extra:
            res['current_attributes_price_extra'] = tuple(current_attributes_price_extra)

        return res

    def _get_attributes_extra_price(self):
        self.ensure_one()

        return sum(self.env.context.get('current_attributes_price_extra', []))

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
        for template in self:
            price = template[price_type] or 0.0
            price_currency = template.currency_id
            if price_type == 'standard_price':
                if not price and template.product_variant_ids:
                    price = template.product_variant_ids[0].standard_price
                price_currency = template.cost_currency_id
            elif price_type == 'list_price':
                price += template._get_attributes_extra_price()

            if uom:
                price = template.uom_id._compute_price(price, uom)

            # Convert from current user company currency to asked one
            # This is right cause a field cannot be in more than one currency
            if currency:
                price = price_currency._convert(price, currency, company, date)

            prices[template.id] = price
        return prices

    def _create_variant_ids(self):
        if not self:
            return
        self.env.flush_all()
        Product = self.env["product.product"]

        variants_to_create = []
        variants_to_activate = Product
        variants_to_unlink = Product

        for tmpl_id in self:
            lines_without_no_variants = tmpl_id.valid_product_template_attribute_line_ids._without_no_variant_attributes()

            all_variants = tmpl_id.with_context(active_test=False).product_variant_ids.sorted(lambda p: (p.active, -p.id))

            current_variants_to_create = []
            current_variants_to_activate = Product

            # adding an attribute with only one value should not recreate product
            # write this attribute on every product to make sure we don't lose them
            single_value_lines = lines_without_no_variants.filtered(lambda ptal: len(ptal.product_template_value_ids._only_active()) == 1)
            if single_value_lines:
                for variant in all_variants:
                    combination = variant.product_template_attribute_value_ids | single_value_lines.product_template_value_ids._only_active()
                    # Do not add single value if the resulting combination would
                    # be invalid anyway.
                    if (
                        len(combination) == len(lines_without_no_variants) and
                        combination.attribute_line_id == lines_without_no_variants
                    ):
                        variant.product_template_attribute_value_ids = combination

            # Set containing existing `product.template.attribute.value` combination
            existing_variants = {
                variant.product_template_attribute_value_ids: variant for variant in all_variants
            }

            # Determine which product variants need to be created based on the attribute
            # configuration. If any attribute is set to generate variants dynamically, skip the
            # process.
            # Technical note: if there is no attribute, a variant is still created because
            # 'not any([])' and 'set([]) not in set([])' are True.
            if not tmpl_id.has_dynamic_attributes():
                # Iterator containing all possible `product.template.attribute.value` combination
                # The iterator is used to avoid MemoryError in case of a huge number of combination.
                all_combinations = itertools.product(*[
                    ptal.product_template_value_ids._only_active() for ptal in lines_without_no_variants
                ])
                # For each possible variant, create if it doesn't exist yet.
                for combination in tmpl_id._filter_combinations_impossible_by_config(
                    all_combinations, ignore_no_variant=True,
                ):
                    if combination in existing_variants:
                        current_variants_to_activate += existing_variants[combination]
                    else:
                        current_variants_to_create.append(tmpl_id._prepare_variant_values(combination))
                        variant_limit = self.env['ir.config_parameter'].sudo().get_param('product.dynamic_variant_limit', 1000)
                        if len(current_variants_to_create) > int(variant_limit):
                            raise UserError(_(
                                'The number of variants to generate is above allowed limit. '
                                'You should either not generate variants for each combination or generate them on demand from the sales order. '
                                'To do so, open the form view of attributes and change the mode of *Create Variants*.'))
                variants_to_create += current_variants_to_create
                variants_to_activate += current_variants_to_activate

            elif existing_variants:
                variants_combinations = [variant.product_template_attribute_value_ids for variant in existing_variants.values()]
                current_variants_to_activate += Product.concat(*[existing_variants[possible_combination]
                    for possible_combination in tmpl_id._filter_combinations_impossible_by_config(variants_combinations, ignore_no_variant=True)
                ])
                variants_to_activate += current_variants_to_activate

            variants_to_unlink += all_variants - current_variants_to_activate

        if variants_to_activate:
            variants_to_activate.write({'active': True})
        if variants_to_create:
            Product.create(variants_to_create)
        if variants_to_unlink:
            variants_to_unlink._unlink_or_archive()
            # prevent change if exclusion deleted template by deleting last variant
            if self.exists() != self:
                raise UserError(_("This configuration of product attributes, values, and exclusions would lead to no possible variant. Please archive or delete your product directly if intended."))
        for variant in variants_to_unlink:
            combo_items_to_unlink = self.env['product.combo.item'].search([
                ('product_id', '=', variant.id)
            ])
            # Unlink all combo items which reference unlinked variants.
            combo_items_to_unlink.unlink()

        # prefetched o2m have to be reloaded (because of active_test)
        # (eg. product.template: product_variant_ids)
        # We can't rely on existing invalidate because of the savepoint
        # in _unlink_or_archive.
        self.env.flush_all()
        self.env.invalidate_all()
        return True

    def _prepare_variant_values(self, combination):
        self.ensure_one()
        return {
            'product_tmpl_id': self.id,
            'product_template_attribute_value_ids': [(6, 0, combination.ids)],
            'active': self.active
        }

    def has_dynamic_attributes(self):
        """Return whether this `product.template` has at least one dynamic
        attribute.

        :return: True if at least one dynamic attribute, False otherwise
        :rtype: bool
        """
        self.ensure_one()
        return any(a.create_variant == 'dynamic' for a in self.valid_product_template_attribute_line_ids.attribute_id)

    @api.depends('attribute_line_ids.value_ids')
    def _compute_valid_product_template_attribute_line_ids(self):
        """A product template attribute line is considered valid if it has at
        least one possible value.

        Those with only one value are considered valid, even though they should
        not appear on the configurator itself (unless they have an is_custom
        value to input), indeed single value attributes can be used to filter
        products among others based on that attribute/value.
        """
        for record in self:
            record.valid_product_template_attribute_line_ids = record.attribute_line_ids.filtered(lambda ptal: ptal.value_ids)

    def _get_possible_variants(self, parent_combination=None):
        """Return the existing variants that are possible.

        For dynamic attributes, it will only return the variants that have been
        created already.

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

    def _get_attribute_exclusions(
        self, parent_combination=None, parent_name=None, combination_ids=None
    ):
        """Return the list of attribute exclusions of a product.

        :param parent_combination: the combination from which
            `self` is an optional or accessory product. Indeed exclusions
            rules on one product can concern another product.
        :type parent_combination: recordset `product.template.attribute.value`
        :param parent_name: the name of the parent product combination.
        :type parent_name: str
        :param list combination: The combination of the product, as a
            list of `product.template.attribute.value` ids.

        :return: dict of exclusions
            - exclusions: from this product itself
            - archived_combinations: list of archived combinations
            - parent_combination: ids of the given parent_combination
            - parent_exclusions: from the parent_combination
           - parent_product_name: the name of the parent product if any, used in the interface
               to explain why some combinations are not available.
               (e.g: Not available with Customizable Desk (Legs: Steel))
           - mapped_attribute_names: the name of every attribute values based on their id,
               used to explain in the interface why that combination is not available
               (e.g: Not available with Color: Black)
        """
        self.ensure_one()
        parent_combination = parent_combination or self.env['product.template.attribute.value']
        archived_products = self.with_context(active_test=False).product_variant_ids.filtered(lambda l: not l.active)
        active_combinations = set(tuple(product.product_template_attribute_value_ids.ids) for product in self.product_variant_ids)
        return {
            'exclusions': self._complete_inverse_exclusions(
                self._get_own_attribute_exclusions(combination_ids=combination_ids)
            ),
            'archived_combinations': list(set(
                tuple(product.product_template_attribute_value_ids.ids)
                for product in archived_products
                if product.product_template_attribute_value_ids and all(
                    ptav.ptav_active or combination_ids and ptav.id in combination_ids
                    for ptav in product.product_template_attribute_value_ids
                )
            ) - active_combinations),
            'parent_exclusions': self._get_parent_attribute_exclusions(parent_combination),
            'parent_combination': parent_combination.ids,
            'parent_product_name': parent_name,
            'mapped_attribute_names': self._get_mapped_attribute_names(parent_combination),
        }

    @api.model
    def _complete_inverse_exclusions(self, exclusions):
        """Will complete the dictionnary of exclusions with their respective inverse
        e.g: Black excludes XL and L
        -> XL excludes Black
        -> L excludes Black"""
        result = dict(exclusions)
        for key, value in exclusions.items():
            for exclusion in value:
                if exclusion in result and key not in result[exclusion]:
                    result[exclusion].append(key)
                else:
                    result[exclusion] = [key]

        return result

    def _get_own_attribute_exclusions(self, combination_ids=None):
        """Get exclusions coming from the current template.

        :param list combination: The combination of the product, as a
            list of `product.template.attribute.value` ids.
        Dictionnary, each product template attribute value is a key, and for each of them
        the value is an array with the other ptav that they exclude (empty if no exclusion).
        """
        self.ensure_one()
        product_template_attribute_values = self.valid_product_template_attribute_line_ids.product_template_value_ids
        return {
            ptav.id: [
                value.id
                for filter_line in ptav.exclude_for.filtered(
                    lambda filter_line: filter_line.product_tmpl_id == self
                ) for value in filter_line.value_ids if value.ptav_active
            ]
            for ptav in product_template_attribute_values if (
                ptav.ptav_active or combination_ids and ptav.id in combination_ids
            )
        }

    def _get_parent_attribute_exclusions(self, parent_combination):
        """Get exclusions coming from the parent combination.

        Dictionnary, each parent's ptav is a key, and for each of them the value is
        an array with the other ptav that are excluded because of the parent.
        """
        self.ensure_one()
        if not parent_combination:
            return {}

        result = {}
        for product_attribute_value in parent_combination:
            for filter_line in product_attribute_value.exclude_for.filtered(
                lambda filter_line: filter_line.product_tmpl_id == self
            ):
                # Some exclusions don't have attribute value. This means that the template is not
                # compatible with the parent combination. If such an exclusion is found, it means that all
                # attribute values are excluded.
                if filter_line.value_ids:
                    result[product_attribute_value.id] = filter_line.value_ids.ids
                else:
                    result[product_attribute_value.id] = filter_line.product_tmpl_id.mapped('attribute_line_ids.product_template_value_ids').ids

        return result

    def _get_mapped_attribute_names(self, parent_combination=None):
        """ The name of every attribute values based on their id,
        used to explain in the interface why that combination is not available
        (e.g: Not available with Color: Black).

        It contains both attribute value names from this product and from
        the parent combination if provided.
        """
        self.ensure_one()
        all_product_attribute_values = self.valid_product_template_attribute_line_ids.product_template_value_ids
        if parent_combination:
            all_product_attribute_values |= parent_combination

        return {
            attribute_value.id: attribute_value.display_name
            for attribute_value in all_product_attribute_values
        }

    def _filter_combinations_impossible_by_config(self, combination_tuples, ignore_no_variant=False):
        """ Filter combination_tuples according to the config of attributes on the template

        :return: iterator over possible combinations
        :rtype: generator
        """
        self.ensure_one()
        attribute_lines = self.valid_product_template_attribute_line_ids
        attribute_lines_active_values = attribute_lines.product_template_value_ids._only_active()
        if ignore_no_variant:
            attribute_lines = attribute_lines._without_no_variant_attributes()
        attribute_lines_without_multi = attribute_lines.filtered(
            lambda l: l.attribute_id.display_type != 'multi')
        exclusions = self._get_own_attribute_exclusions()
        for combination_tuple in combination_tuples:
            combination = self.env['product.template.attribute.value'].concat(*combination_tuple)
            combination_without_multi = combination.filtered(
                lambda l: l.attribute_line_id.attribute_id.display_type != 'multi')
            if len(combination_without_multi) != len(attribute_lines_without_multi):
                # number of attribute values passed is different than the
                # configuration of attributes on the template
                continue
            if attribute_lines_without_multi != combination_without_multi.attribute_line_id:
                # combination has different attributes than the ones configured on the template
                continue
            if not (attribute_lines_active_values >= combination):
                # combination has different values than the ones configured on the template
                continue
            if exclusions:
                # exclude if the current value is in an exclusion,
                # and the value excluding it is also in the combination
                combination_ids = set(combination.ids)
                combination_excluded_ids = set(itertools.chain(*[exclusions.get(ptav_id) for ptav_id in combination.ids]))
                if combination_ids & combination_excluded_ids:
                    continue
            yield combination

    def _is_combination_possible_by_config(self, combination, ignore_no_variant=False):
        """Return whether the given combination is possible according to the config of attributes on the template

        :param combination: the combination to check for possibility
        :type combination: recordset `product.template.attribute.value`

        :param ignore_no_variant: whether no_variant attributes should be ignored
        :type ignore_no_variant: bool

        :return: wether the given combination is possible according to the config of attributes on the template
        :rtype: bool
        """
        self.ensure_one()
        # Returns False on StopIteration. Empty combination should return True.
        return isinstance(next(self._filter_combinations_impossible_by_config([combination], ignore_no_variant), False), models.BaseModel)

    def _is_combination_possible(self, combination, parent_combination=None, ignore_no_variant=False):
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

        :param ignore_no_variant: whether no_variant attributes should be ignored
        :type ignore_no_variant: bool

        :param parent_combination: combination from which `self` is an
            optional or accessory product.
        :type parent_combination: recordset `product.template.attribute.value`

        :return: whether the combination is possible
        :rtype: bool
        """
        self.ensure_one()

        if not self._is_combination_possible_by_config(combination, ignore_no_variant):
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

        parent_exclusions = self._get_parent_attribute_exclusions(parent_combination)
        if parent_exclusions:
            # parent_exclusion are mapped by ptav but here we don't need to know
            # where the exclusion comes from so we loop directly on the dict values
            for exclusions_values in parent_exclusions.values():
                for exclusion in exclusions_values:
                    if exclusion in combination.ids:
                        return False

        return True

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
        return self.env['product.product'].browse(self._get_variant_id_for_combination(filtered_combination))

    def _create_product_variant(self, combination, log_warning=False):
        """ Create if necessary and possible and return the product variant
        matching the given combination for this template.

        It is possible to create only if the template has dynamic attributes
        and the combination itself is possible.
        If we are in this case and the variant already exists but it is
        archived, it is activated instead of being created again.

        :param combination: the combination for which to get or create variant.
            The combination must contain all necessary attributes, including
            those of type no_variant. Indeed even though those attributes won't
            be included in the variant if newly created, they are needed when
            checking if the combination is possible.
        :type combination: recordset of `product.template.attribute.value`

        :param log_warning: whether a warning should be logged on fail
        :type log_warning: bool

        :return: the product variant matching the combination or none
        :rtype: recordset of `product.product`
        """
        self.ensure_one()

        Product = self.env['product.product']

        product_variant = self._get_variant_for_combination(combination)
        if product_variant:
            if not product_variant.active and self.has_dynamic_attributes() and self._is_combination_possible(combination):
                product_variant.active = True
            return product_variant

        if not self.has_dynamic_attributes():
            if log_warning:
                _logger.warning('The user #%s tried to create a variant for the non-dynamic product %s.' % (self.env.user.id, self.id))
            return Product

        if not self._is_combination_possible(combination):
            if log_warning:
                _logger.warning('The user #%s tried to create an invalid variant for the product %s.' % (self.env.user.id, self.id))
            return Product

        return Product.sudo().create({
            'product_tmpl_id': self.id,
            'product_template_attribute_value_ids': [(6, 0, combination._without_no_variant_attributes().ids)]
        })

    def _create_first_product_variant(self, log_warning=False):
        """Create if necessary and possible and return the first product
        variant for this template.

        :param log_warning: whether a warning should be logged on fail
        :type log_warning: bool

        :return: the first product variant or none
        :rtype: recordset of `product.product`
        """
        return self._create_product_variant(self._get_first_possible_combination(), log_warning)

    @tools.ormcache('self.id', 'frozenset(filtered_combination.ids)')
    def _get_variant_id_for_combination(self, filtered_combination):
        """See `_get_variant_for_combination`. This method returns an ID
        so it can be cached.

        Use sudo because the same result should be cached for all users.
        """
        self.ensure_one()
        domain = [('product_tmpl_id', '=', self.id)]
        combination_indices_ids = filtered_combination._ids2str()

        if combination_indices_ids:
            domain = expression.AND([domain, [('combination_indices', '=', combination_indices_ids)]])
        else:
            domain = expression.AND([domain, [('combination_indices', 'in', ['', False])]])

        return self.env['product.product'].sudo().with_context(active_test=False).search(domain, order='active DESC', limit=1).id

    @tools.ormcache('self.id')
    def _get_first_possible_variant_id(self):
        """See `_create_first_product_variant`. This method returns an ID
        so it can be cached."""
        self.ensure_one()
        return self._create_first_product_variant().id

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

            # For multi-checkbox attribute, the list is empty as we want to start without any selected value
            if not current_line_values:
                if line_index == len(product_template_attribute_values_per_line) - 1:
                    # submit combination if we're on the last line
                    yield partial_combination
                else:
                    line_index += 1
                    continue

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
        necessary_attribute_lines = necessary_values.mapped('attribute_line_id')
        attribute_lines = self.valid_product_template_attribute_line_ids.filtered(
            lambda ptal: ptal not in necessary_attribute_lines)

        if not attribute_lines and self._is_combination_possible(necessary_values, parent_combination):
            yield necessary_values

        product_template_attribute_values_per_line = []
        for ptal in attribute_lines:
            if ptal.attribute_id.display_type != 'multi':
                values_to_add = ptal.product_template_value_ids._only_active()
            else:
                values_to_add = self.env['product.template.attribute.value']
            product_template_attribute_values_per_line.append(values_to_add)

        for partial_combination in self._cartesian_product(product_template_attribute_values_per_line, parent_combination):
            combination = partial_combination + necessary_values
            if self._is_combination_possible(combination, parent_combination):
                yield combination

        return _("There are no remaining possible combination.")

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

    def _get_placeholder_filename(self, field):
        image_fields = ['image_%s' % size for size in [1920, 1024, 512, 256, 128]]
        if field in image_fields:
            return 'product/static/img/placeholder_thumbnail.png'
        return super()._get_placeholder_filename(field)

    def get_single_product_variant(self):
        """ Method used by the product configurator to check if the product is configurable or not.

        We need to open the product configurator if the product:
        - is configurable (see has_configurable_attributes)
        - has optional products (method is extended in sale to return optional products info)

        Note: self.ensure_one()
        """
        self.ensure_one()
        if self.product_variant_count == 1 and not self.has_configurable_attributes:
            return {
                'product_id': self.product_variant_id.id,
                'product_name': self.product_variant_id.display_name,
            }
        return {}

    @api.model
    def get_empty_list_help(self, help_message):
        self = self.with_context(
            empty_list_help_document_name=_("product"),
        )
        return super(ProductTemplate, self).get_empty_list_help(help_message)

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Products'),
            'template': '/product/static/xls/product_template.xls'
        }]

    def get_contextual_price(self, product=None):
        return self._get_contextual_price(product=product)

    def _get_contextual_price(self, product=None):
        self.ensure_one()
        pricelist = self._get_contextual_pricelist()
        quantity = self.env.context.get('quantity', 1.0)
        uom = self.env['uom.uom'].browse(self.env.context.get('uom'))
        date = self.env.context.get('date')
        return pricelist._get_product_price(product or self, quantity, uom=uom, date=date)

    def _get_contextual_pricelist(self):
        """ Get the contextual pricelist

        This method is meant to be overriden in other standard modules.
        """
        return self.env['product.pricelist'].browse(self.env.context.get('pricelist'))

    ###################
    # DEMO DATA SETUP #
    ###################

    @api.model
    def _demo_configure_variants(self):
        acoustic_bloc_screens = self.env.ref(
            'product.product_template_acoustic_bloc_screens', raise_if_not_found=False
        )
        if acoustic_bloc_screens:
            acoustic_bloc_screens.product_variant_ids[0].default_code = 'FURN_6666'
            acoustic_bloc_screens.product_variant_ids[1].default_code = 'FURN_6667'
            self.env['ir.model.data']._update_xmlids([{
                'xml_id': 'product.product_product_25',
                'record': acoustic_bloc_screens.product_variant_ids[1],
                'noupdate': True,
            }])

    def _get_list_price(self, price):
        """ Get the product sales price from a public price based on taxes defined on the product.
        To be overridden in accounting module."""
        self.ensure_one()
        return price

    @api.model
    def _service_tracking_blacklist(self):
        """ Service tracking field is used to distinguish some specific categories of products.
        Those products shouldn't be displayed or used in unrelated applications.
        This method returns a domain targeting all those specific products (events, courses, ...).
        """
        return []
