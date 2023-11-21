# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import SUPERUSER_ID, api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import is_html_empty


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

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if self.sale_order_template_id and self.sale_order_template_id.number_of_days > 0:
            default = dict(default or {})
            default['validity_date'] = fields.Date.context_today(self) + timedelta(self.sale_order_template_id.number_of_days)
        return super(SaleOrder, self).copy(default=default)

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        super(SaleOrder, self).onchange_partner_id()
        template = self.sale_order_template_id.with_context(lang=self.partner_id.lang)
        self.note = template.note if not is_html_empty(template.note) else self.note

    def _compute_line_data_for_template_change(self, line):
        return {
            'display_type': line.display_type,
            'name': line.name,
            'state': 'draft',
        }

    def _compute_option_data_for_template_change(self, option):
        price = option.product_id.lst_price
        discount = 0

        if self.pricelist_id:
            pricelist_price = self.pricelist_id.with_context(uom=option.uom_id.id).get_product_price(option.product_id, 1, False)

            if self.pricelist_id.discount_policy == 'without_discount' and price:
                discount = max(0, (price - pricelist_price) * 100 / price)
            else:
                price = pricelist_price

        return {
            'product_id': option.product_id.id,
            'name': option.name,
            'quantity': option.quantity,
            'uom_id': option.uom_id.id,
            'price_unit': price,
            'discount': discount
        }

    def update_prices(self):
        self.ensure_one()
        res = super().update_prices()
        self.sale_order_option_ids._update_price_and_discount()
        return res

    @api.onchange('sale_order_template_id')
    def onchange_sale_order_template_id(self):

        if not self.sale_order_template_id:
            self.require_signature = self._get_default_require_signature()
            self.require_payment = self._get_default_require_payment()
            return

        template = self.sale_order_template_id.with_context(lang=self.partner_id.lang)

        # --- first, process the list of products from the template
        order_lines = [(5, 0, 0)]
        for line in template.sale_order_template_line_ids:
            data = self._compute_line_data_for_template_change(line)

            if line.product_id:
                price = line.product_id.lst_price
                discount = 0

                if self.pricelist_id:
                    pricelist_price = self.pricelist_id.with_context(uom=line.product_uom_id.id).get_product_price(line.product_id, 1, False)

                    if self.pricelist_id.discount_policy == 'without_discount' and price:
                        discount = max(0, (price - pricelist_price) * 100 / price)
                    else:
                        price = pricelist_price

                data.update({
                    'price_unit': price,
                    'discount': discount,
                    'product_uom_qty': line.product_uom_qty,
                    'product_id': line.product_id.id,
                    'product_uom': line.product_uom_id.id,
                    'customer_lead': self._get_customer_lead(line.product_id.product_tmpl_id),
                })

            order_lines.append((0, 0, data))

        # set first line to sequence -99, so a resequence on first page doesn't cause following page
        # lines (that all have sequence 10 by default) to get mixed in the first page
        if len(order_lines) >= 2:
            order_lines[1][2]['sequence'] = -99

        self.order_line = order_lines
        self.order_line._compute_tax_id()

        # then, process the list of optional products from the template
        option_lines = [(5, 0, 0)]
        for option in template.sale_order_template_option_ids:
            data = self._compute_option_data_for_template_change(option)
            option_lines.append((0, 0, data))

        self.sale_order_option_ids = option_lines

        if template.number_of_days > 0:
            self.validity_date = fields.Date.context_today(self) + timedelta(template.number_of_days)

        self.require_signature = template.require_signature
        self.require_payment = template.require_payment

        if not is_html_empty(template.note):
            self.note = template.note

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        if self.env.su:
            self = self.with_user(SUPERUSER_ID)

        for order in self:
            if order.sale_order_template_id and order.sale_order_template_id.mail_template_id:
                order.sale_order_template_id.mail_template_id.send_mail(order.id)
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

    # Take the description on the order template if the product is present in it
    @api.onchange('product_id')
    def product_id_change(self):
        domain = super(SaleOrderLine, self).product_id_change()
        if self.product_id and self.order_id.sale_order_template_id:
            for line in self.order_id.sale_order_template_id.sale_order_template_line_ids:
                if line.product_id == self.product_id:
                    lang = self.order_id.partner_id.lang
                    self.name = line.with_context(lang=lang).name + self.with_context(lang=lang)._get_sale_order_line_multiline_description_variants()
                    break
        return domain


class SaleOrderOption(models.Model):
    _name = "sale.order.option"
    _description = "Sale Options"
    _order = 'sequence, id'

    is_present = fields.Boolean(string="Present on Quotation",
                           help="This field will be checked if the option line's product is "
                                "already present in the quotation.",
                           compute="_compute_is_present", search="_search_is_present")
    order_id = fields.Many2one('sale.order', 'Sales Order Reference', ondelete='cascade', index=True)
    line_id = fields.Many2one('sale.order.line', ondelete="set null", copy=False)
    name = fields.Text('Description', required=True)
    product_id = fields.Many2one('product.product', 'Product', required=True, domain=[('sale_ok', '=', True)])
    price_unit = fields.Float('Unit Price', required=True, digits='Product Price')
    discount = fields.Float('Discount (%)', digits='Discount')
    uom_id = fields.Many2one('uom.uom', 'Unit of Measure ', required=True, domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id', readonly=True)
    quantity = fields.Float('Quantity', required=True, digits='Product Unit of Measure', default=1)
    sequence = fields.Integer('Sequence', help="Gives the sequence order when displaying a list of optional products.")

    def _update_price_and_discount(self):
        for option in self:
            if not option.product_id:
                continue
            # To compute the discount a so line is created in cache
            values = option._get_values_to_add_to_order()
            new_sol = option.env['sale.order.line'].new(values)
            new_sol._onchange_discount()
            option.discount = new_sol.discount
            if option.order_id.pricelist_id and option.order_id.partner_id:
                product = option.product_id.with_context(
                    partner=option.order_id.partner_id,
                    quantity=option.quantity,
                    date=option.order_id.date_order,
                    pricelist=option.order_id.pricelist_id.id,
                    uom=option.uom_id.id,
                    fiscal_position=option.env.context.get('fiscal_position')
                )
                option.price_unit = new_sol._get_display_price(product)

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

    @api.onchange('product_id', 'uom_id', 'quantity')
    def _onchange_product_id(self):
        if not self.product_id:
            return
        product = self.product_id.with_context(
            lang=self.order_id.partner_id.lang,
        )
        self.uom_id = self.uom_id or product.uom_id
        self.name = product.get_product_multiline_description_sale()
        self._update_price_and_discount()

    def button_add_to_order(self):
        self.add_option_to_order()

    def add_option_to_order(self):
        self.ensure_one()

        sale_order = self.order_id

        if sale_order.state not in ['draft', 'sent']:
            raise UserError(_('You cannot add options to a confirmed order.'))

        values = self._get_values_to_add_to_order()
        order_line = self.env['sale.order.line'].create(values)
        order_line._compute_tax_id()

        self.write({'line_id': order_line.id})
        if sale_order:
            sale_order.add_option_to_order_with_taxcloud()


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
            'company_id': self.order_id.company_id.id,
        }
