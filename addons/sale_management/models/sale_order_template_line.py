# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrderTemplateLine(models.Model):
    _name = 'sale.order.template.line'
    _description = "Quotation Template Line"
    _order = 'sale_order_template_id, sequence, id'

    _accountable_product_id_required = models.Constraint(
        'CHECK(display_type IS NOT NULL OR (product_id IS NOT NULL AND product_uom_id IS NOT NULL))',
        'Missing required product and UoM on accountable sale quote line.',
    )
    _non_accountable_fields_null = models.Constraint(
        'CHECK(display_type IS NULL OR (product_id IS NULL AND product_uom_qty = 0 AND product_uom_id IS NULL))',
        'Forbidden product, quantity and UoM on non-accountable sale quote line',
    )

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
        translate=True,
    )

    allowed_uom_ids = fields.Many2many('uom.uom', compute='_compute_allowed_uom_ids')
    product_uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string="Unit of Measure",
        domain="[('id', 'in', allowed_uom_ids)]",
        compute='_compute_product_uom_id',
        store=True, readonly=False, precompute=True)
    product_uom_qty = fields.Float(
        string='Quantity',
        required=True,
        digits='Product Unit',
        default=1)

    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False)

    #=== COMPUTE METHODS ===#

    @api.depends('product_id', 'product_id.uom_id', 'product_id.uom_ids')
    def _compute_allowed_uom_ids(self):
        for option in self:
            option.allowed_uom_ids = option.product_id.uom_id | option.product_id.uom_ids

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
        return [('sale_ok', '=', True), ('type', '!=', 'combo')]

    def _prepare_order_line_values(self):
        """ Give the values to create the corresponding order line.

        :return: `sale.order.line` create values
        :rtype: dict
        """
        self.ensure_one()
        vals = {
            'display_type': self.display_type,
            'product_id': self.product_id.id,
            'product_uom_qty': self.product_uom_qty,
            'product_uom_id': self.product_uom_id.id,
            'sequence': self.sequence,
        }
        if self.name:
            vals['name'] = self.name
        return vals
