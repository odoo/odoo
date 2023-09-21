# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrderTemplateLine(models.Model):
    _name = "sale.order.template.line"
    _description = "Quotation Template Line"
    _order = 'sale_order_template_id, sequence, id'

    _sql_constraints = [
        ('accountable_product_id_required',
            "CHECK(display_type IS NOT NULL OR (product_id IS NOT NULL AND product_uom_id IS NOT NULL))",
            "Missing required product and UoM on accountable sale quote line."),

        ('non_accountable_fields_null',
            "CHECK(display_type IS NULL OR (product_id IS NULL AND product_uom_qty = 0 AND product_uom_id IS NULL))",
            "Forbidden product, quantity and UoM on non-accountable sale quote line"),
    ]

    sale_order_template_id = fields.Many2one(
        comodel_name='sale.order.template',
        string='Quotation Template Reference',
        index=True, required=True,
        ondelete='cascade')
    sequence = fields.Integer(
        string="Sequence",
        help="Gives the sequence order when displaying a list of sale quote lines.",
        default=10)

    company_id = fields.Many2one(
        related='sale_order_template_id.company_id', store=True, index=True)

    product_id = fields.Many2one(
        comodel_name='product.product',
        check_company=True,
        domain=lambda self: self._product_id_domain())

    name = fields.Text(
        string="Description",
        compute='_compute_name',
        store=True, readonly=False, precompute=True,
        required=True,
        translate=True)

    product_uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string="Unit of Measure",
        compute='_compute_product_uom_id',
        store=True, readonly=False, precompute=True,
        domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    product_uom_qty = fields.Float(
        string='Quantity',
        required=True,
        digits='Product Unit of Measure',
        default=1)

    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False)

    #=== COMPUTE METHODS ===#

    @api.depends('product_id')
    def _compute_name(self):
        for option in self:
            if not option.product_id:
                continue
            option.name = option.product_id.get_product_multiline_description_sale()

    @api.depends('product_id')
    def _compute_product_uom_id(self):
        for option in self:
            option.product_uom_id = option.product_id.uom_id

    #=== CRUD METHODS ===#

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('display_type', self.default_get(['display_type'])['display_type']):
                vals.update(product_id=False, product_uom_qty=0, product_uom_id=False)
        return super().create(vals_list)

    def write(self, values):
        if 'display_type' in values and self.filtered(lambda line: line.display_type != values.get('display_type')):
            raise UserError(_("You cannot change the type of a sale quote line. Instead you should delete the current line and create a new line of the proper type."))
        return super().write(values)

    #=== BUSINESS METHODS ===#

    @api.model
    def _product_id_domain(self):
        """ Returns the domain of the products that can be added to the template. """
        return [('sale_ok', '=', True)]

    def _prepare_order_line_values(self):
        """ Give the values to create the corresponding order line.

        :return: `sale.order.line` create values
        :rtype: dict
        """
        self.ensure_one()
        return {
            'display_type': self.display_type,
            'name': self.name,
            'product_id': self.product_id.id,
            'product_uom_qty': self.product_uom_qty,
            'product_uom': self.product_uom_id.id,
        }
