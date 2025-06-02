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

    @api.depends('product_tmpl_ids')
    def _compute_number_related_products(self):
        res = {
            attribute.id: count
            for attribute, count in self.env['product.template.attribute.line']._read_group(
                domain=[('attribute_id', 'in', self.ids)],
                groupby=['attribute_id'],
                aggregates=['product_tmpl_id:count_distinct'],
            )
        }
        for pa in self:
            pa.number_related_products = res.get(pa.id, 0)

    @api.depends('attribute_line_ids.active', 'attribute_line_ids.product_tmpl_id')
    def _compute_products(self):
        for pa in self:
            pa.with_context(active_test=False).product_tmpl_ids = pa.attribute_line_ids.product_tmpl_id

    def _without_no_variant_attributes(self):
        return self.filtered(lambda pa: pa.create_variant != 'no_variant')

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

    def action_open_related_products(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _("Related Products"),
            'res_model': 'product.template',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.with_context(active_test=False).product_tmpl_ids.ids)],
        }
