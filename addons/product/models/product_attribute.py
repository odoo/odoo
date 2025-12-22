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
    active = fields.Boolean(
        default=True,
        help="If unchecked, it will allow you to hide the attribute without removing it.",
    )
    create_variant = fields.Selection(
        selection=[
            ('always', 'Instantly'),
            ('dynamic', 'Dynamically'),
            ('no_variant', 'Never'),
        ],
        default='always',
        string="Variant Creation",
        help="""- Instantly: All possible variants are created as soon as the attribute and its values are added to a product.
        - Dynamically: Each variant is created only when its corresponding attributes and values are added to a sales order.
        - Never: Variants are never created for the attribute.
        Note: this cannot be changed once the attribute is used on a product.""",
        required=True)
    display_type = fields.Selection(
        selection=[
            ('radio', 'Radio'),
            ('pills', 'Pills'),
            ('select', 'Select'),
            ('color', 'Color'),
            ('multi', 'Multi-checkbox'),
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
                domain=[('attribute_id', 'in', self.ids), ('product_tmpl_id.active', '=', 'True')],
                groupby=['attribute_id'],
                aggregates=['__count'],
            )
        }
        for pa in self:
            pa.number_related_products = res.get(pa.id, 0)

    @api.depends('attribute_line_ids.active', 'attribute_line_ids.product_tmpl_id')
    def _compute_products(self):
        templates_by_attribute = {
            attribute.id: templates
            for attribute, templates in self.env['product.template.attribute.line']._read_group(
                domain=[('attribute_id', 'in', self.ids)],
                groupby=['attribute_id'],
                aggregates=['product_tmpl_id:recordset']
            )
        }
        for pa in self:
            pa.with_context(active_test=False).product_tmpl_ids = templates_by_attribute.get(pa.id, False)

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
                raise UserError(_(
                    "You cannot delete the attribute %(attribute)s because it is used on the"
                    " following products:\n%(products)s",
                    attribute=pa.display_name,
                    products=", ".join(pa.product_tmpl_ids.mapped('display_name')),
                ))

    # === ACTION METHODS === #

    def action_archive(self):
        for attribute in self:
            if attribute.number_related_products:
                raise UserError(_(
                    "You cannot archive this attribute as there are still products linked to it",
                ))
        return super().action_archive()

    def action_open_product_template_attribute_lines(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Products"),
            'res_model': 'product.template.attribute.line',
            'view_mode': 'list,form',
            'domain': [('attribute_id', '=', self.id), ('product_tmpl_id.active', '=', 'True')],
        }

    # === TOOLING === #

    def _without_no_variant_attributes(self):
        return self.filtered(lambda pa: pa.create_variant != 'no_variant')
