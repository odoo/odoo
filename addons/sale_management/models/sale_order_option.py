# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrderOption(models.Model):
    _name = 'sale.order.option'
    _description = "Sale Options"
    _order = 'sequence, id'

    # FIXME ANVFE wtf is it not required ???
    # TODO related to order.company_id and restrict product choice based on company
    order_id = fields.Many2one('sale.order', 'Sales Order Reference', ondelete='cascade', index=True)

    product_id = fields.Many2one(
        comodel_name='product.product',
        required=True,
        domain=lambda self: self._product_id_domain())
    line_id = fields.Many2one(
        comodel_name='sale.order.line', ondelete='set null', copy=False)
    sequence = fields.Integer(
        string='Sequence', help="Gives the sequence order when displaying a list of optional products.")

    name = fields.Text(
        string="Description",
        compute='_compute_name',
        store=True, readonly=False,
        required=True, precompute=True)

    quantity = fields.Float(
        string="Quantity",
        required=True,
        digits='Product Unit of Measure',
        default=1)
    allowed_uom_ids = fields.Many2many('uom.uom', compute='_compute_allowed_uom_ids')
    uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string="Unit of Measure",
        compute='_compute_uom_id',
        domain="[('id', 'in', allowed_uom_ids)]",
        store=True, readonly=False,
        required=True, precompute=True)

    price_unit = fields.Float(
        string="Unit Price",
        digits='Product Price',
        compute='_compute_price_unit',
        store=True, readonly=False,
        required=True, precompute=True)
    discount = fields.Float(
        string="Discount (%)",
        digits='Discount',
        compute='_compute_discount',
        store=True, readonly=False, precompute=True)

    is_present = fields.Boolean(
        string="Present on Quotation",
        compute='_compute_is_present',
        search='_search_is_present',
        help="This field will be checked if the option line's product is "
             "already present in the quotation.")

    #=== COMPUTE METHODS ===#

    @api.depends('product_id', 'product_id.uom_id', 'product_id.uom_ids')
    def _compute_allowed_uom_ids(self):
        for option in self:
            option.allowed_uom_ids = option.product_id.uom_id | option.product_id.uom_ids

    @api.depends('product_id')
    def _compute_name(self):
        for option in self:
            if not option.product_id:
                continue
            product_lang = option.product_id.with_context(lang=option.order_id.partner_id.lang)
            option.name = product_lang.get_product_multiline_description_sale()

    @api.depends('product_id')
    def _compute_uom_id(self):
        for option in self:
            if not option.product_id or option.uom_id:
                continue
            option.uom_id = option.product_id.uom_id

    @api.depends('product_id', 'uom_id', 'quantity')
    def _compute_price_unit(self):
        for option in self:
            if not option.product_id:
                continue
            # To compute the price_unit a so line is created in cache
            values = option._get_values_to_add_to_order()
            new_sol = self.env['sale.order.line'].new(values)
            new_sol._compute_price_unit()
            option.price_unit = new_sol.price_unit
            # Avoid attaching the new line when called on template change
            new_sol.order_id = False

    @api.depends('product_id', 'uom_id', 'quantity')
    def _compute_discount(self):
        for option in self:
            if not option.product_id:
                continue
            # To compute the discount a so line is created in cache
            values = option._get_values_to_add_to_order()
            new_sol = self.env['sale.order.line'].new(values)
            new_sol._compute_discount()
            option.discount = new_sol.discount
            # Avoid attaching the new line when called on template change
            new_sol.order_id = False

    def _get_values_to_add_to_order(self):
        self.ensure_one()
        return {
            'order_id': self.order_id.id,
            'price_unit': self.price_unit,
            'technical_price_unit': self.price_unit,
            'name': self.name,
            'product_id': self.product_id.id,
            'product_uom_qty': self.quantity,
            'product_uom_id': self.uom_id.id,
            'discount': self.discount,
            'sequence': max(self.order_id.order_line.mapped('sequence'), default=0) + 1
        }

    @api.depends('line_id', 'order_id.order_line', 'product_id')
    def _compute_is_present(self):
        # NOTE: this field cannot be stored as the line_id is usually removed
        # through cascade deletion, which means the compute would be false
        for option in self:
            option.is_present = bool(option.order_id.order_line.filtered(lambda l: l.product_id == option.product_id))

    def _search_is_present(self, operator, value):
        if (operator, value) in [('=', True), ('!=', False)]:
            return [('line_id', '=', False)]
        return [('line_id', '!=', False)]

    @api.model
    def _product_id_domain(self):
        """ Returns the domain of the products that can be added as a sale order option. """
        return [('sale_ok', '=', True)]

    #=== ACTION METHODS ===#

    def button_add_to_order(self):
        self.add_option_to_order()

    def add_option_to_order(self):
        self.ensure_one()

        if not self.order_id._can_be_edited_on_portal():
            raise UserError(_('You cannot add options to a confirmed order.'))

        values = self._get_values_to_add_to_order()
        order_line = self.env['sale.order.line'].create(values)

        self.write({'line_id': order_line.id})

        return order_line
