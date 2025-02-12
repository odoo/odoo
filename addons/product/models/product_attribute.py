# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProductAttribute(models.Model):
    _name = "product.attribute"
    _description = "Product Attribute"
    # if you change this _order, keep it in sync with the method
    # `_sort_key_attribute_value` in `product.template`
    _order = 'sequence, id'

    _sql_constraints = [
        (
            'check_multi_checkbox_no_variant',
            "CHECK(display_type != 'multi' OR create_variant = 'no_variant')",
            "Multi-checkbox display type is not compatible with the creation of variants"
        ),
    ]

    name = fields.Char(string="Attribute", required=True, translate=True)
    create_variant = fields.Selection(
        selection=[
            ('always', 'Instantly'),
            ('dynamic', 'Dynamically'),
            ('no_variant', 'Never (option)'),
        ],
        default='always',
        string="Variants Creation Mode",
        help="""- Instantly: All possible variants are created as soon as the attribute and its values are added to a product.
        - Dynamically: Each variant is created only when its corresponding attributes and values are added to a sales order.
        - Never: Variants are never created for the attribute.
        Note: the variants creation mode cannot be changed once the attribute is used on at least one product.""",
        required=True)
    display_type = fields.Selection(
        selection=[
            ('radio', 'Radio'),
            ('pills', 'Pills'),
            ('select', 'Select'),
            ('color', 'Color'),
            ('multi', 'Multi-checkbox (option)'),
        ],
        default='radio',
        required=True,
        help="The display type used in the Product Configurator.")
    sequence = fields.Integer(string="Sequence", help="Determine the display order", index=True, default=20)

    value_ids = fields.One2many(
        comodel_name='product.attribute.value',
        inverse_name='attribute_id',
        string="Values", copy=True)
    template_value_ids = fields.One2many(
        comodel_name='product.template.attribute.value',
        inverse_name='attribute_id',
        string="Template Values")
    attribute_line_ids = fields.One2many(
        comodel_name='product.template.attribute.line',
        inverse_name='attribute_id',
        string="Lines")
    product_tmpl_ids = fields.Many2many(
        comodel_name='product.template',
        string="Related Products",
        compute='_compute_products',
        store=True)
    number_related_products = fields.Integer(compute='_compute_number_related_products')

    # === COMPUTE METHODS === #

    @api.depends('product_tmpl_ids')
    def _compute_number_related_products(self):
        res = {
            attribute.id: count
            for attribute, count in self.env['product.template.attribute.line']._read_group(
                domain=[('attribute_id', 'in', self.ids)],
                groupby=['attribute_id'],
                aggregates=['__count'],
            )
        }
        for pa in self:
            pa.number_related_products = res.get(pa.id, 0)

    @api.depends('attribute_line_ids.active', 'attribute_line_ids.product_tmpl_id')
    def _compute_products(self):
        for pa in self:
            pa.with_context(active_test=False).product_tmpl_ids = pa.attribute_line_ids.product_tmpl_id

    # === ONCHANGE METHODS === #

    @api.onchange('display_type')
    def _onchange_display_type(self):
        if self.display_type == 'multi' and self.number_related_products == 0:
            self.create_variant = 'no_variant'

    # === CRUD METHODS === #

    def write(self, vals):
        """Override to make sure attribute type can't be changed if it's used on
        a product template.

        This is important to prevent because changing the type would make
        existing combinations invalid without recomputing them, and recomputing
        them might take too long and we don't want to change products without
        the user knowing about it."""
        if 'create_variant' in vals:
            for pa in self:
                if vals['create_variant'] != pa.create_variant and pa.number_related_products:
                    raise UserError(_(
                        "You cannot change the Variants Creation Mode of the attribute %(attribute)s"
                        " because it is used on the following products:\n%(products)s",
                        attribute=pa.display_name,
                        products=", ".join(pa.product_tmpl_ids.mapped('display_name')),
                    ))
        invalidate = 'sequence' in vals and any(record.sequence != vals['sequence'] for record in self)
        res = super().write(vals)
        if invalidate:
            # prefetched o2m have to be resequenced
            # (eg. product.template: attribute_line_ids)
            self.env.flush_all()
            self.env.invalidate_all()
        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_except_used_on_product(self):
        for pa in self:
            if pa.number_related_products:
                raise UserError(
                    _("You cannot delete the attribute %s because it is used on the following products:\n%s") %
                    (pa.display_name, ", ".join(pa.product_tmpl_ids.mapped('display_name')))
                )

    def action_open_related_products(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _("Related Products"),
            'res_model': 'product.template',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.with_context(active_test=False).product_tmpl_ids.ids)],
        }


class ProductAttributeValue(models.Model):
    _name = "product.attribute.value"
    # if you change this _order, keep it in sync with the method
    # `_sort_key_variant` in `product.template'
    _order = 'attribute_id, sequence, id'
    _description = 'Attribute Value'

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char(string='Value', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', help="Determine the display order", index=True)
    attribute_id = fields.Many2one('product.attribute', string="Attribute", ondelete='cascade', required=True, index=True,
        help="The attribute cannot be changed once the value is used on at least one product.")

    pav_attribute_line_ids = fields.Many2many('product.template.attribute.line', string="Lines",
        relation='product_attribute_value_product_template_attribute_line_rel', copy=False)
    is_used_on_products = fields.Boolean('Used on Products', compute='_compute_is_used_on_products')

    is_custom = fields.Boolean('Is custom value', help="Allow users to input custom values for this attribute value")
    html_color = fields.Char(
        string='Color',
        help="Here you can set a specific HTML color index (e.g. #ff0000) to display the color if the attribute type is 'Color'.")
    display_type = fields.Selection(related='attribute_id.display_type', readonly=True)
    color = fields.Integer('Color Index', default=_get_default_color)

    _sql_constraints = [
        ('value_company_uniq', 'unique (name, attribute_id)', "You cannot create two values with the same name for the same attribute.")
    ]

    @api.depends('pav_attribute_line_ids')
    def _compute_is_used_on_products(self):
        for pav in self:
            pav.is_used_on_products = bool(pav.pav_attribute_line_ids)

    def name_get(self):
        """Override because in general the name of the value is confusing if it
        is displayed without the name of the corresponding attribute.
        Eg. on product list & kanban views, on BOM form view

        However during variant set up (on the product template form) the name of
        the attribute is already on each line so there is no need to repeat it
        on every value.
        """
        if not self._context.get('show_attribute', True):
            return super(ProductAttributeValue, self).name_get()
        return [(value.id, "%s: %s" % (value.attribute_id.name, value.name)) for value in self]

    def write(self, values):
        if 'attribute_id' in values:
            for pav in self:
                if pav.attribute_id.id != values['attribute_id'] and pav.is_used_on_products:
                    raise UserError(
                        _("You cannot change the attribute of the value %s because it is used on the following products:%s") %
                        (pav.display_name, ", ".join(pav.pav_attribute_line_ids.product_tmpl_id.mapped('display_name')))
                    )

        invalidate = 'sequence' in values and any(record.sequence != values['sequence'] for record in self)
        res = super(ProductAttributeValue, self).write(values)
        if invalidate:
            # prefetched o2m have to be resequenced
            # (eg. product.template.attribute.line: value_ids)
            self.env.flush_all()
            self.env.invalidate_all()
        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_except_used_on_product(self):
        for pav in self:
            if pav.is_used_on_products:
                raise UserError(
                    _("You cannot delete the value %s because it is used on the following products:"
                      "\n%s\n If the value has been associated to a product in the past, you will "
                      "not be able to delete it.") %
                    (pav.display_name, ", ".join(
                        pav.pav_attribute_line_ids.product_tmpl_id.mapped('display_name')
                    ))
                )
            linked_products = pav.env['product.template.attribute.value'].search(
                [('product_attribute_value_id', '=', pav.id)]
            ).with_context(active_test=False).ptav_product_variant_ids
            unlinkable_products = linked_products._filter_to_unlink()
            if linked_products != unlinkable_products:
                raise UserError(_(
                    "You cannot delete the attribute %(attribute)s because it is used on the"
                    " following products:\n%(products)s",
                    attribute=pa.display_name,
                    products=", ".join(pa.product_tmpl_ids.mapped('display_name')),
                ))

    # === ACTION METHODS === #

    def action_open_product_template_attribute_lines(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Products"),
            'res_model': 'product.template.attribute.line',
            'view_mode': 'tree,form',
            'domain': [('attribute_id', '=', self.id)],
        }

    # === TOOLING === #

    def _without_no_variant_attributes(self):
        return self.filtered(lambda pa: pa.create_variant != 'no_variant')
