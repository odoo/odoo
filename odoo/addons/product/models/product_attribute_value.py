# Part of Odoo. See LICENSE file for full copyright and licensing details.

from random import randint

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProductAttributeValue(models.Model):
    _name = 'product.attribute.value'
    # if you change this _order, keep it in sync with the method
    # `_sort_key_variant` in `product.template'
    _order = 'attribute_id, sequence, id'
    _description = "Attribute Value"

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char(string="Value", required=True, translate=True)
    sequence = fields.Integer(string="Sequence", help="Determine the display order", index=True)
    attribute_id = fields.Many2one(
        comodel_name='product.attribute',
        string="Attribute",
        help="The attribute cannot be changed once the value is used on at least one product.",
        ondelete='cascade',
        required=True,
        index=True)

    pav_attribute_line_ids = fields.Many2many(
        comodel_name='product.template.attribute.line',
        relation='product_attribute_value_product_template_attribute_line_rel',
        string="Lines",
        copy=False)
    is_used_on_products = fields.Boolean(
        string="Used on Products", compute='_compute_is_used_on_products')

    default_extra_price = fields.Float()
    is_custom = fields.Boolean(
        string="Is custom value",
        help="Allow users to input custom values for this attribute value")
    html_color = fields.Char(
        string="Color",
        help="Here you can set a specific HTML color index (e.g. #ff0000)"
            " to display the color if the attribute type is 'Color'.")
    display_type = fields.Selection(related='attribute_id.display_type')
    color = fields.Integer(string="Color Index", default=_get_default_color)
    image = fields.Image(
        string="Image",
        help="You can upload an image that will be used as the color of the attribute value.",
        max_width=70,
        max_height=70,
    )

    _sql_constraints = [
        ('value_company_uniq',
         'unique (name, attribute_id)',
         "You cannot create two values with the same name for the same attribute.")
    ]

    @api.depends('pav_attribute_line_ids')
    def _compute_is_used_on_products(self):
        for pav in self:
            pav.is_used_on_products = bool(pav.pav_attribute_line_ids)

    @api.depends('attribute_id')
    @api.depends_context('show_attribute')
    def _compute_display_name(self):
        """Override because in general the name of the value is confusing if it
        is displayed without the name of the corresponding attribute.
        Eg. on product list & kanban views, on BOM form view

        However during variant set up (on the product template form) the name of
        the attribute is already on each line so there is no need to repeat it
        on every value.
        """
        if not self.env.context.get('show_attribute', True):
            return super()._compute_display_name()
        for value in self:
            value.display_name = f"{value.attribute_id.name}: {value.name}"

    def write(self, values):
        if 'attribute_id' in values:
            for pav in self:
                if pav.attribute_id.id != values['attribute_id'] and pav.is_used_on_products:
                    raise UserError(_(
                        "You cannot change the attribute of the value %(value)s because it is used"
                        " on the following products: %(products)s",
                        value=pav.display_name,
                        products=", ".join(pav.pav_attribute_line_ids.product_tmpl_id.mapped('display_name')),
                    ))

        invalidate = 'sequence' in values and any(record.sequence != values['sequence'] for record in self)
        res = super().write(values)
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
                raise UserError(_(
                    "You cannot delete the value %(value)s because it is used on the following "
                    "products:\n%(products)s\n If the value has been associated to a product in the"
                    " past, you will not be able to delete it.",
                    value=pav.display_name,
                    products=", ".join(pav.pav_attribute_line_ids.product_tmpl_id.mapped('display_name')),
                ))
            linked_products = pav.env['product.template.attribute.value'].search(
                [('product_attribute_value_id', '=', pav.id)]
            ).with_context(active_test=False).ptav_product_variant_ids
            unlinkable_products = linked_products._filter_to_unlink()
            if linked_products != unlinkable_products:
                raise UserError(_(
                    "You cannot delete value %s because it was used in some products.",
                    pav.display_name
                ))

    def _without_no_variant_attributes(self):
        return self.filtered(lambda pav: pav.attribute_id.create_variant != 'no_variant')
