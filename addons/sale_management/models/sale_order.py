# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def default_get(self, fields_list):
        default_vals = super(SaleOrder, self).default_get(fields_list)
        if "sale_order_template_id" in fields_list and not default_vals.get("sale_order_template_id"):
            company_id = default_vals.get('company_id', False)
            company = self.env["res.company"].browse(company_id) if company_id else self.env.company
            default_vals['sale_order_template_id'] = company.sale_order_template_id.id
        return default_vals

    sale_order_template_id = fields.Many2one(
        'sale.order.template', 'Quotation Template',
        readonly=True, check_company=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    sale_order_option_ids = fields.One2many(
        'sale.order.option', 'order_id', 'Optional Products Lines',
        copy=True, readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if self.sale_order_template_id and self.sale_order_template_id.number_of_days > 0:
            default = dict(default or {})
            default['validity_date'] = fields.Date.context_today(self) + timedelta(self.sale_order_template_id.number_of_days)
        return super(SaleOrder, self).copy(default=default)

    @api.depends('partner_id', 'company_id', 'sale_order_template_id')
    def _compute_note(self):
        super()._compute_note()

    def _get_note(self):
        return self.sale_order_template_id.note or super()._get_note()

    @api.depends('company_id', 'sale_order_template_id')
    def _compute_company_defaults(self):
        template_based_order = self.filtered('sale_order_template_id')
        for order in template_based_order:
            template = order.sale_order_template_id
            order.require_signature = template.require_signature
            order.require_payment = template.require_payment
            order.validity_date = template.number_of_days > 0 and \
                fields.Date.to_string(fields.Datetime.now() + timedelta(template.number_of_days))
        super(SaleOrder, self-template_based_order)._compute_company_defaults()

    @api.onchange('sale_order_template_id')
    def onchange_sale_order_template_id(self):
        self = self.with_context(lang=self.partner_id.lang)
        template = self.sale_order_template_id

        # --- first, process the list of products from the template
        order_lines = [(5, 0, 0)] + [
            (0, 0, line._prepare_soline_values()) for line in template.sale_order_template_line_ids
        ]

        self.order_line = order_lines

        # then, process the list of optional products from the template
        option_lines = [(5, 0, 0)] + [
            (0, 0, option._prepare_sooption_values()) for option in template.sale_order_template_option_ids
        ]

        self.sale_order_option_ids = option_lines

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            if order.sale_order_template_id and order.sale_order_template_id.mail_template_id:
                self.sale_order_template_id.mail_template_id.send_mail(order.id)
        return res

    def get_access_action(self, access_uid=None):
        """ Instead of the classic form view, redirect to the online quote if it exists. """
        self.ensure_one()
        user = access_uid and self.env['res.users'].sudo().browse(access_uid) or self.env.user

        if not self.sale_order_template_id or (not user.share and not self.env.context.get('force_website')):
            return super(SaleOrder, self).get_access_action(access_uid)
        return {
            'type': 'ir.actions.act_url',
            'url': self.get_portal_url(),
            'target': 'self',
            'res_id': self.id,
        }


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    _description = "Sales Order Line"

    sale_order_option_ids = fields.One2many('sale.order.option', 'line_id', 'Optional Products Lines')


class SaleOrderOption(models.Model):
    _name = "sale.order.option"
    _description = "Sale Options"
    _order = 'sequence, id'
    _check_company_auto = True

    order_id = fields.Many2one('sale.order', 'Sales Order Reference', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='order_id.company_id', store=True)
    currency_id = fields.Many2one(related='order_id.currency_id', store=True)

    name = fields.Text('Description', compute="_compute_name", store=True, readonly=False)
    product_id = fields.Many2one(
        'product.product', string='Product',
        domain="[('sale_ok', '=', True), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        change_default=True, ondelete='restrict', check_company=True)

    uom_id = fields.Many2one(
        'uom.uom', 'Unit of Measure ',
        compute="_compute_product_information", store=True, readonly=False,
        domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    quantity = fields.Float(
        'Quantity', digits='Product Unit of Measure',
        compute="_compute_product_information", store=True, readonly=False)

    price_unit = fields.Float(
        'Unit Price', digits='Product Price',
        compute="_compute_price_unit", store=True, readonly=False)
    discount = fields.Float(
        string='Discount (%)', digits='Discount', copy=True,
        compute="_compute_price_unit", store=True, readonly=False)
    line_id = fields.Many2one('sale.order.line', ondelete="set null", copy=False)
    is_present = fields.Boolean(
        string="Present on Quotation",
        compute="_compute_is_present", search="_search_is_present",
        help="This field will be checked if the option line's product is "
        "already present in the quotation.")

    sequence = fields.Integer('Sequence', help="Gives the sequence order when displaying a list of optional products.")

    # VFE FEEDBACK
    # Do we want the price shown for the option to be the fucking final price when added on order ?
    # Then we need to consider taxes and pricelist discount on options
    # Otherwise, probably remove discount bc it's confusing what to do with it?
    # final SO line should have both discounts?

    # TODO dependency on pricelist and compute discount on it also for the option lines.
    @api.depends('product_id', 'company_id', 'quantity', 'uom_id')
    def _compute_price_unit(self):
        discount_enabled = self.user_has_groups("product.group_discount_per_so_line")
        for option in self:
            if option.order_id.pricelist_id and option.product_id and option.uom_id:
                option = option.with_context(
                    partner_id=option.order_id.partner_id.id,
                    quantity=option.quantity,
                    date=option.order_id.date_order or fields.Date.today(),
                    pricelist=option.order_id.pricelist_id.id,
                    uom=option.uom_id.id
                ).with_company(option.company_id)
                product = option.product_id
                discount = 0.0
                price, rule_id = option.order_id.pricelist_id.get_product_price_rule(
                    product, option.quantity, option.order_id.partner_id
                )
                if discount_enabled and option.order_id.pricelist_id.discount_policy == "without_discount":
                    new_list_price, currency = option.env["sale.order.line"]._get_real_price_currency(
                        product, rule_id, option.quantity, option.uom_id, option.order_id.pricelist_id.id
                    )
                    if new_list_price != 0:
                        if option.currency_id != currency:
                            # we need new_list_price in the same currency as price, which is in the SO's pricelist's currency
                            new_list_price = currency._convert(
                                from_amount=new_list_price,
                                to_currency=option.currency_id,
                                company=option.env.company,
                                date=option.order_id.date_order or fields.Date.today())
                        disc = (new_list_price - price) / new_list_price * 100
                        if (disc > 0 and new_list_price > 0) or (disc < 0 and new_list_price < 0):
                            discount = disc
                        price = new_list_price
                option.price_unit = price
                # option.env['account.tax']._fix_tax_included_price_company(
                #     price, product.taxes_id, option.tax_id, option.env.company)
                option.discount = discount or option.discount
            else:
                option.price_unit = 0.0
                option.discount = 0.0

    @api.depends('product_id')
    def _compute_product_information(self):
        for option in self:
            option.uom_id = option.product_id.uom_id  # if category different else option.uom_id ?
            option.quantity = 1.0

    @api.depends('product_id')
    def _compute_name(self):
        for option in self:
            if option.order_id.partner_id:
                option = option.with_context(lang=option.order_id.partner_id)
            option.name = option.product_id.get_product_multiline_description_sale()

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

    # VFE TODO remove one of the two methods ???
    def button_add_to_order(self):
        self.add_option_to_order()

    def add_option_to_order(self):
        self.ensure_one()

        if self.order_id.state not in ['draft', 'sent']:
            raise UserError(_('You cannot add options to a confirmed order.'))

        values = self._get_values_to_add_to_order()
        order_line = self.env['sale.order.line'].create(values)

        self.write({'line_id': order_line.id})

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
