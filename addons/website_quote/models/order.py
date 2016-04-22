# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid
from datetime import datetime, timedelta

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp


class SaleQuoteTemplate(models.Model):
    _name = "sale.quote.template"
    _description = "Sale Quotation Template"

    name = fields.Char('Quotation Template', required=True)
    website_description = fields.Html('Description', translate=True)
    quote_line = fields.One2many('sale.quote.line', 'quote_id', 'Quotation Template Lines', copy=True)
    note = fields.Text('Terms and conditions')
    options = fields.One2many('sale.quote.option', 'template_id', 'Optional Products Lines', copy=True)
    number_of_days = fields.Integer('Quotation Duration', help='Number of days for the validity date computation of the quotation')
    require_payment = fields.Selection([
        (0, 'Not mandatory on website quote validation'),
        (1, 'Immediate after website order validation')
        ], 'Payment', help="Require immediate payment by the customer when validating the order from the website quote")
    mail_template_id = fields.Many2one('mail.template', 'Confirmation Mail', help="This e-mail template will be sent on confirmation. Leave empty to send nothing.")

    @api.multi
    def open_template(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '/quote/template/%d' % self.id
        }


class SaleQuoteLine(models.Model):
    _name = "sale.quote.line"
    _description = "Quotation Template Lines"
    _order = 'sequence, id'

    sequence = fields.Integer(default=10, help="Gives the sequence order when displaying a list of sale quote lines.")
    quote_id = fields.Many2one('sale.quote.template', 'Quotation Template Reference', required=True, ondelete='cascade', select=True)
    name = fields.Text('Description', required=True, translate=True)
    product_id = fields.Many2one('product.product', 'Product', domain=[('sale_ok', '=', True)], required=True)
    layout_category_id = fields.Many2one('sale.layout_category', string='Section')
    website_description = fields.Html(related="product_id.product_tmpl_id.quote_description", string='Line Description', translate=True)
    price_unit = fields.Float('Unit Price', required=True, digits_compute=dp.get_precision('Product Price'))
    discount = fields.Float('Discount (%)', defualt=0.0, digits_compute=dp.get_precision('Discount'))
    product_uom_qty = fields.Float('Quantity', required=True, default=1, digits_compute=dp.get_precision('Product UoS'))
    product_uom_id = fields.Many2one('product.uom', 'Unit of Measure ', required=True)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.ensure_one()
        product = self.product_id
        if product:
            name = product.name
            if product.description_sale:
                name += '\n' + product.description_sale
            self.name = name
            self.price_unit = product.lst_price
            self.product_uom_id = product.uom_id.id
            self.website_description = product.quote_description or product.website_description
            domain = {'product_uom_id': [('category_id', '=', product.uom_id.category_id.id)]}
            return {'domain': domain}

    @api.onchange('product_uom_id')
    def _onchange_product_uom(self):
        if self.product_id and self.product_uom_id:
            self.price_unit = self.product_id.uom_id._compute_price(self.product_id.uom_id.id, self.product_id.lst_price, self.product_uom_id.id)

    def _inject_quote_description(self, values):
        values = dict(values or {})
        if not values.get('website_description') and values.get('product_id'):
            product = self.env['product.product'].browse(values['product_id'])
            values['website_description'] = product.quote_description or product.website_description or ''
        return values

    @api.model
    def create(self, values):
        values = self._inject_quote_description(values)
        return super(SaleQuoteLine, self).create(values)

    @api.multi
    def write(self, values):
        values = self._inject_quote_description(values)
        return super(SaleQuoteLine, self).write(values)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    _description = "Sales Order Line"

    website_description = fields.Html('Line Description')
    option_line_id = fields.One2many('sale.order.option', 'line_id', 'Optional Products Lines')

    def _inject_quote_description(self, values):
        values = dict(values or {})
        if not values.get('website_description') and values.get('product_id'):
            product = self.env['product.product'].browse(values['product_id'])
            values['website_description'] = product.quote_description or product.website_description
        return values

    @api.model
    def create(self, values):
        values = self._inject_quote_description(values)
        return super(SaleOrderLine, self).create(values)

    @api.multi
    def write(self, values):
        values = self._inject_quote_description(values)
        return super(SaleOrderLine, self).write(values)

    # Take the description on the order template if the product is present in it
    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        domain = super(SaleOrderLine, self).product_id_change()
        if self.order_id.template_id:
            self.name = next((quote_line.name for quote_line in self.order_id.template_id.quote_line if quote_line.product_id.id == self.product_id.id), self.name)
        return domain


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def get_default_template(self):
        template = self.env.ref('website_quote.website_quote_template_default', raise_if_not_found=False)
        return template if template else self.env['sale.quote.template']

    access_token = fields.Char('Security Token', default=lambda self: str(uuid.uuid4()), required=True, copy=False)
    template_id = fields.Many2one('sale.quote.template', 'Quotation Template', default=get_default_template, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})
    website_description = fields.Html('Description', translate=True)
    options = fields.One2many('sale.order.option', 'order_id', 'Optional Products Lines', readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, copy=True)
    amount_undiscounted = fields.Float(compute='_compute_undiscounted_amount', string='Amount Before Discount', digits=0)
    quote_viewed = fields.Boolean('Quotation Viewed')
    require_payment = fields.Selection([
        (0, 'Not mandatory on website quote validation'),
        (1, 'Immediate after website order validation')
        ], 'Payment', help="Require immediate payment by the customer when validating the order from the website quote")

    def _compute_undiscounted_amount(self):
        for order in self:
            total = 0.0
            for line in order.order_line:
                total += line.price_subtotal + line.price_unit * ((line.discount or 0.0) / 100.0) * line.product_uom_qty
            self.total = total

    @api.multi
    def open_quotation(self):
        self.ensure_one()
        self.quote_viewed = True
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '/quote/%s/%s' % (self.id, self.access_token)
        }

    @api.onchange('template_id', 'partner_id')
    def _onchange_template_id(self):
        if not self.template_id:
            return
        if self.partner_id:
            self = self.with_context(lang=self.partner_id.lang)

        order_lines = [(5,)]
        for line in self.template_id.quote_line:
            if self.pricelist_id:
                price = self.pricelist_id.with_context(uom=line.product_uom_id.id).price_get(line.product_id.id, qty=1)[self.pricelist_id.id]
            else:
                price = line.price_unit
            data = {
                'name': line.name,
                'price_unit': price,
                'discount': line.discount,
                'product_uom_qty': line.product_uom_qty,
                'product_id': line.product_id.id,
                'layout_category_id': line.layout_category_id,
                'product_uom': line.product_uom_id.id,
                'website_description': line.website_description,
                'state': 'draft',
                'customer_lead': self._get_customer_lead(line.product_id.product_tmpl_id),
            }
            order_lines.append((0, 0, data))
        self.order_line = order_lines
        self.order_line._compute_tax_id()
        option_lines = []
        for option in self.template_id.options:
            if self.pricelist_id:
                price = self.pricelist_id.with_context(uom=option.uom_id.id).price_get(option.product_id.id, qty=1)[self.pricelist_id.id]
            else:
                price = option.price_unit
            data = {
                'product_id': option.product_id.id,
                'layout_category_id': option.layout_category_id,
                'name': option.name,
                'quantity': option.quantity,
                'uom_id': option.uom_id.id,
                'price_unit': price,
                'discount': option.discount,
                'website_description': option.website_description,
            }
            option_lines.append((0, 0, data))
        self.options = option_lines

        if self.template_id.number_of_days > 0:
            self.validity_date = fields.Date.to_string(datetime.now() + timedelta(self.template_id.number_of_days))

        if self.template_id.note:
            self.note = self.template_id.note

        self.website_description = self.template_id.website_description
        self.require_payment = self.template_id.require_payment

    @api.multi
    def get_access_action(self):
        """ Override method that generated the link to access the document. Instead
        of the classic form view, redirect to the online quote if exists. """
        self.ensure_one()
        if not self.template_id:
            return super(SaleOrder, self).get_access_action()
        return {
            'type': 'ir.actions.act_url',
            'url': '/quote/%s/%s' % (self.id, self.access_token),
            'target': 'self',
            'res_id': self.id,
        }

    def _confirm_online_quote(self, transaction):
        """ Payment callback: validate the order and write transaction details in chatter """
        # create draft invoice if transaction is ok
        if transaction.state == 'done':
            if self.state in ['draft', 'sent']:
                self.sudo().action_confirm()
            message = _('Order paid by %s. Transaction: %s. Amount: %s.') % (transaction.partner_id.name, transaction.acquirer_reference, transaction.amount)
            self.message_post(body=message)
            return True
        return False

    @api.multi
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            if order.template_id and order.template_id.mail_template_id:
                order.template_id.mail_template_id.send_mail(order.id)
        return res

    def _get_payment_type(self):
        return 'form'

class SaleQuoteOption(models.Model):
    _name = "sale.quote.option"
    _description = "Quotation Option"

    template_id = fields.Many2one('sale.quote.template', 'Quotation Template Reference', ondelete='cascade', select=True, required=True)
    name = fields.Text('Description', required=True, translate=True)
    product_id = fields.Many2one('product.product', 'Product', domain=[('sale_ok', '=', True)], required=True)
    layout_category_id = fields.Many2one('sale.layout_category', string='Section')
    website_description = fields.Html('Option Description', translate=True)
    price_unit = fields.Float('Unit Price', required=True, digits_compute=dp.get_precision('Product Price'))
    discount = fields.Float('Discount (%)', digits_compute=dp.get_precision('Discount'))
    uom_id = fields.Many2one('product.uom', 'Unit of Measure ', required=True)
    quantity = fields.Float('Quantity', default=1, required=True, digits_compute=dp.get_precision('Product UoS'))

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if not self.product_id:
            return
        product = self.product_id
        self.price_unit = product.list_price
        self.website_description = product.product_tmpl_id.quote_description
        self.name = product.name
        self.uom_id = product.uom_id
        domain = {'uom_id': [('category_id', '=', self.product_id.uom_id.category_id.id)]}
        return {'domain': domain}

    @api.onchange('uom_id')
    def _onchange_product_uom(self):
        if not self.product_id:
            return
        if not self.uom_id:
            self.price_unit = 0.0
            return
        if self.uom_id.id != self.product_id.uom_id.id:
            self.price_unit = self.product_id.uom_id._compute_price(self.product_id.uom_id.id, self.price_unit, self.uom_id.id)

class SaleOrderOption(models.Model):
    _name = "sale.order.option"
    _description = "Sale Options"
    _order = 'sequence, id'

    order_id = fields.Many2one('sale.order', 'Sale Order Reference', ondelete='cascade', select=True)
    line_id = fields.Many2one('sale.order.line', on_delete="set null")
    name = fields.Text('Description', required=True)
    product_id = fields.Many2one('product.product', 'Product', domain=[('sale_ok', '=', True)])
    layout_category_id = fields.Many2one('sale.layout_category', string='Section')
    website_description = fields.Html('Line Description')
    price_unit = fields.Float('Unit Price', required=True, digits_compute=dp.get_precision('Product Price'))
    discount = fields.Float('Discount (%)', digits_compute=dp.get_precision('Discount'))
    uom_id = fields.Many2one('product.uom', 'Unit of Measure ', required=True)
    quantity = fields.Float('Quantity', default=1, required=True,
        digits_compute=dp.get_precision('Product UoS'))
    sequence = fields.Integer('Sequence', help="Gives the sequence order when displaying a list of suggested product.")

    @api.onchange('product_id', 'uom_id')
    def _onchange_product_id(self):
        if not self.product_id:
            return
        product = self.product_id.with_context(lang=self.order_id.partner_id.lang)
        self.price_unit = product.list_price
        self.website_description = product.quote_description or product.website_description
        self.name = product.name
        if product.description_sale:
            self.name += '\n' + product.description_sale
        self.uom_id = self.uom_id or product.uom_id
        pricelist = self.order_id.pricelist_id
        if pricelist and product:
            partner_id = self.order_id.partner_id.id
            self.price_unit = pricelist.with_context(uom=self.uom_id.id).price_get(product.id, self.quantity, partner_id)[pricelist.id]
        domain = {'uom_id': [('category_id', '=', self.product_id.uom_id.category_id.id)]}
        return {'domain': domain}

    @api.multi
    def button_add_to_order(self):
        self.ensure_one()
        order = self.order_id
        if order.state not in ['draft', 'sent']:
            return False
        option = self

        order_line = order.order_line.filtered(lambda line: line.product_id == option.product_id)
        if order_line:
            order_line[0].product_uom_qty += 1
        else:
            vals = {
                'price_unit': option.price_unit,
                'website_description': option.website_description,
                'name': option.name,
                'order_id': order.id,
                'product_id': option.product_id.id,
                'layout_category_id': option.layout_category_id.id,
                'product_uom_qty': option.quantity,
                'product_uom': option.uom_id.id,
                'discount': option.discount,
            }
            order_line = self.env['sale.order.line'].create(vals)

        order_line._compute_tax_id()
        option.line_id = order_line[0]
        return {'type': 'ir.actions.client', 'tag': 'reload'}


class ProductTemplate(models.Model):
    _inherit = "product.template"

    website_description = fields.Html('Description for the website')  # hack, if website_sale is not installed
    quote_description = fields.Html('Description for the quote')
