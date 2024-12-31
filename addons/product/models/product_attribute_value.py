# Part of Odoo. See LICENSE file for full copyright and licensing details.

from random import randint

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProductAttributeValue(models.Model):
    # if you change this _order, keep it in sync with the method
    # `_sort_key_variant` in `product.template'
    _name = 'product.attribute.value'
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

    default_extra_price = fields.Float()
    is_custom = fields.Boolean(
        string="Free text",
        help="Allow customers to set their own value")
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
    active = fields.Boolean(default=True)

    is_used_on_products = fields.Boolean(
        string="Used on Products", compute='_compute_is_used_on_products')
    default_extra_price_changed = fields.Boolean(compute='_compute_default_extra_price_changed')

    # === COMPUTE METHODS === #

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

    @api.depends('pav_attribute_line_ids')
    def _compute_is_used_on_products(self):
        for pav in self:
            pav.is_used_on_products = bool(pav.pav_attribute_line_ids.filtered(lambda rec: rec.product_tmpl_id.active))

    @api.depends('default_extra_price')
    def _compute_default_extra_price_changed(self):
        for pav in self:
            pav.default_extra_price_changed = (
                pav.default_extra_price != pav._origin.default_extra_price
            )

    # === CRUD METHODS === #

    def write(self, vals):
        if 'attribute_id' in vals:
            for pav in self:
                if pav.attribute_id.id != vals['attribute_id'] and pav.is_used_on_products:
                    raise UserError(_(
                        "You cannot change the attribute of the value %(value)s because it is used"
                        " on the following products: %(products)s",
                        value=pav.display_name,
                        products=", ".join(pav.pav_attribute_line_ids.product_tmpl_id.mapped('display_name')),
                    ))

        invalidate = 'sequence' in vals and any(record.sequence != vals['sequence'] for record in self)
        res = super().write(vals)
        if invalidate:
            # prefetched o2m have to be resequenced
            # (eg. product.template.attribute.line: value_ids)
            self.env.flush_all()
            self.env.invalidate_all()
        return res

    def check_is_used_on_products(self):
        for pav in self.filtered('is_used_on_products'):
            return _(
                "You cannot delete the value %(value)s because it is used on the following"
                " products:\n%(products)s\n",
                value=pav.display_name,
                products=", ".join(pav.pav_attribute_line_ids.product_tmpl_id.mapped('display_name')),
            )
        return False

    @api.ondelete(at_uninstall=False)
    def _unlink_except_used_on_product(self):
        if is_used_on_products := self.check_is_used_on_products():
            raise UserError(is_used_on_products)

    def unlink(self):
        pavs_to_archive = self.env['product.attribute.value']
        for pav in self:
            linked_products = pav.env['product.template.attribute.value'].search(
                [('product_attribute_value_id', '=', pav.id)]
            ).with_context(active_test=False).ptav_product_variant_ids
            active_linked_products = linked_products.filtered('active')
            if not active_linked_products:
                # If product attribute value found on non-active product variants
                # archive PAV instead of deleting
                pavs_to_archive |= pav
        if pavs_to_archive:
            pavs_to_archive.action_archive()
        return super(ProductAttributeValue, self - pavs_to_archive).unlink()

    def _without_no_variant_attributes(self):
        return self.filtered(lambda pav: pav.attribute_id.create_variant != 'no_variant')

    # === ACTION METHODS === #

    @api.readonly
    def action_add_to_products(self):
        return {
            'name': _("Add to all products"),
            'type': 'ir.actions.act_window',
            'res_model': 'update.product.attribute.value',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_attribute_value_id': self.id,
                'default_mode': 'add',
                'dialog_size': 'medium',
            },
        }

    @api.readonly
    def action_update_prices(self):
        return {
            'name': _("Update product extra prices"),
            'type': 'ir.actions.act_window',
            'res_model': 'update.product.attribute.value',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_attribute_value_id': self.id,
                'default_mode': 'update_extra_price',
                'dialog_size': 'medium',
            },
        }
