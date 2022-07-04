# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import SUPERUSER_ID, api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import is_html_empty

from odoo.addons.sale.models.sale_order import READONLY_FIELD_STATES


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    sale_order_template_id = fields.Many2one(
        comodel_name='sale.order.template',
        string="Quotation Template",
        compute='_compute_sale_order_template_id',
        store=True, readonly=False, check_company=True, precompute=True,
        states=READONLY_FIELD_STATES,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    sale_order_option_ids = fields.One2many(
        comodel_name='sale.order.option', inverse_name='order_id',
        string="Optional Products Lines",
        states=READONLY_FIELD_STATES,
        copy=True)

    #=== COMPUTE METHODS ===#

    @api.depends('company_id')
    def _compute_sale_order_template_id(self):
        for order in self:
            if order._origin.id:  # If record has already been saved
                # 1) Do NOT update existing SO's template and dependent fields
                # Especially when installing sale_management in a db
                # already containing SO records
                # 2) Only apply the company default if the company is modified before the record is saved
                # to make sure the lines are not magically reset when the company is modified (internal odoo issue)
                continue
            company_template = order.company_id.sale_order_template_id
            if company_template and order.sale_order_template_id != company_template:
                order.sale_order_template_id = order.company_id.sale_order_template_id.id

    @api.depends('partner_id', 'sale_order_template_id')
    def _compute_note(self):
        super()._compute_note()
        for order in self.filtered('sale_order_template_id'):
            template = order.sale_order_template_id.with_context(lang=order.partner_id.lang)
            order.note = template.note if not is_html_empty(template.note) else order.note

    @api.depends('sale_order_template_id')
    def _compute_require_signature(self):
        super()._compute_require_signature()
        for order in self.filtered('sale_order_template_id'):
            order.require_signature = order.sale_order_template_id.require_signature

    @api.depends('sale_order_template_id')
    def _compute_require_payment(self):
        super()._compute_require_payment()
        for order in self.filtered('sale_order_template_id'):
            order.require_payment = order.sale_order_template_id.require_payment

    @api.depends('sale_order_template_id')
    def _compute_validity_date(self):
        super()._compute_validity_date()
        for order in self.filtered('sale_order_template_id'):
            validity_days = order.sale_order_template_id.number_of_days
            if validity_days > 0:
                order.validity_date = fields.Date.context_today(order) + timedelta(validity_days)

    #=== CONSTRAINT METHODS ===#

    @api.constrains('company_id', 'sale_order_option_ids')
    def _check_optional_product_company_id(self):
        for order in self:
            companies = order.sale_order_option_ids.product_id.company_id
            if companies and companies != order.company_id:
                bad_products = order.sale_order_option_ids.product_id.filtered(lambda p: p.company_id and p.company_id != order.company_id)
                raise ValidationError(_(
                    "Your quotation contains products from company %(product_company)s whereas your quotation belongs to company %(quote_company)s. \n Please change the company of your quotation or remove the products from other companies (%(bad_products)s).",
                    product_company=', '.join(companies.mapped('display_name')),
                    quote_company=order.company_id.display_name,
                    bad_products=', '.join(bad_products.mapped('display_name')),
                ))

    #=== ONCHANGE METHODS ===#

    # TODO convert to compute ???
    @api.onchange('sale_order_template_id')
    def _onchange_sale_order_template_id(self):
        sale_order_template = self.sale_order_template_id.with_context(lang=self.partner_id.lang)

        order_lines_data = [fields.Command.clear()]
        order_lines_data += [
            fields.Command.create(
                self._compute_line_data_for_template_change(line)
            )
            for line in sale_order_template.sale_order_template_line_ids
        ]

        self.order_line = order_lines_data

        option_lines_data = [fields.Command.clear()]
        option_lines_data += [
            fields.Command.create(
                self._compute_option_data_for_template_change(option)
            )
            for option in sale_order_template.sale_order_template_option_ids
        ]

        self.sale_order_option_ids = option_lines_data

    # TODO delegate to sub models (note: overridden in sale_quotation_builder)

    def _compute_line_data_for_template_change(self, line):
        return {
            'sequence': line.sequence,
            'display_type': line.display_type,
            'name': line.name,
            'product_id': line.product_id.id,
            'product_uom_qty': line.product_uom_qty,
            'product_uom': line.product_uom_id.id,
        }

    def _compute_option_data_for_template_change(self, option):
        return {
            'name': option.name,
            'product_id': option.product_id.id,
            'quantity': option.quantity,
            'uom_id': option.uom_id.id,
        }

    #=== ACTION METHODS ===#

    def action_confirm(self):
        res = super().action_confirm()
        if self.env.su:
            self = self.with_user(SUPERUSER_ID)

        for order in self:
            if order.sale_order_template_id and order.sale_order_template_id.mail_template_id:
                order.sale_order_template_id.mail_template_id.send_mail(order.id)
        return res

    def update_prices(self):
        super().update_prices()
        # Special case: we want to overwrite the existing discount on update_prices call
        # i.e. to make sure the discount is correctly reset
        # if pricelist discount_policy is different than when the price was first computed.
        self.sale_order_option_ids.discount = 0.0
        self.sale_order_option_ids._compute_price_unit()
        self.sale_order_option_ids._compute_discount()


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    _description = "Sales Order Line"

    sale_order_option_ids = fields.One2many('sale.order.option', 'line_id', 'Optional Products Lines')

    @api.depends('product_id')
    def _compute_name(self):
        # Take the description on the order template if the product is present in it
        super()._compute_name()
        for line in self:
            if line.product_id and line.order_id.sale_order_template_id:
                for template_line in line.order_id.sale_order_template_id.sale_order_template_line_ids:
                    if line.product_id == template_line.product_id:
                        lang = line.order_id.partner_id.lang
                        line.name = template_line.with_context(lang=lang).name + line.with_context(lang=lang)._get_sale_order_line_multiline_description_variants()
                        break


class SaleOrderOption(models.Model):
    _name = "sale.order.option"
    _description = "Sale Options"
    _order = 'sequence, id'

    # FIXME ANVFE wtf is it not required ???
    # TODO related to order.company_id and restrict product choice based on company
    order_id = fields.Many2one('sale.order', 'Sales Order Reference', ondelete='cascade', index=True)

    product_id = fields.Many2one(
        comodel_name='product.product',
        required=True,
        domain=[('sale_ok', '=', True)])
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
    uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string="Unit of Measure",
        compute='_compute_uom_id',
        store=True, readonly=False,
        required=True, precompute=True,
        domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')

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
            if not option.product_id or not option.order_id.pricelist_id:
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
            'name': self.name,
            'product_id': self.product_id.id,
            'product_uom_qty': self.quantity,
            'product_uom': self.uom_id.id,
            'discount': self.discount,
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

    #=== ACTION METHODS ===#

    def button_add_to_order(self):
        self.add_option_to_order()

    def add_option_to_order(self):
        self.ensure_one()

        sale_order = self.order_id

        if sale_order.state not in ['draft', 'sent']:
            raise UserError(_('You cannot add options to a confirmed order.'))

        values = self._get_values_to_add_to_order()
        order_line = self.env['sale.order.line'].create(values)

        self.write({'line_id': order_line.id})
        if sale_order:
            sale_order.add_option_to_order_with_taxcloud()
