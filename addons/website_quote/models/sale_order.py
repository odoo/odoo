# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.tools.translate import html_translate
from odoo.addons import decimal_precision as dp

from werkzeug.urls import url_encode


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    _description = "Sales Order Line"

    website_description = fields.Html('Line Description', sanitize=False, translate=html_translate)
    option_line_id = fields.One2many('sale.order.option', 'line_id', 'Optional Products Lines')

    # Take the description on the order template if the product is present in it
    @api.onchange('product_id')
    def product_id_change(self):
        domain = super(SaleOrderLine, self).product_id_change()
        if self.order_id.template_id:
            self.name = next((quote_line.name for quote_line in self.order_id.template_id.quote_line if
                             quote_line.product_id.id == self.product_id.id), self.name)
        return domain

    @api.model
    def create(self, values):
        values = self._inject_quote_description(values)
        return super(SaleOrderLine, self).create(values)

    @api.multi
    def write(self, values):
        values = self._inject_quote_description(values)
        return super(SaleOrderLine, self).write(values)

    def _inject_quote_description(self, values):
        values = dict(values or {})
        if not values.get('website_description') and values.get('product_id'):
            product = self.env['product.product'].browse(values['product_id'])
            values['website_description'] = product.quote_description or product.website_description
        return values


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _get_default_template(self):
        template = self.env.ref('website_quote.website_quote_template_default', raise_if_not_found=False)
        return template and template.active and template or False

    def _get_default_online_payment(self):
        default_template = self._get_default_template()
        if self.template_id:
            return self.template_id.require_payment
        elif default_template:
            return default_template.require_payment
        elif self.env['ir.config_parameter'].sudo().get_param('sale.sale_portal_confirmation_options', default='none') == 'pay':
            return 1
        else:
            return 0

    template_id = fields.Many2one(
        'sale.quote.template', 'Quotation Template',
        readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        default=_get_default_template)
    website_description = fields.Html('Description', sanitize_attributes=False, translate=html_translate)
    options = fields.One2many(
        'sale.order.option', 'order_id', 'Optional Products Lines',
        copy=True, readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})
    amount_undiscounted = fields.Float(
        'Amount Before Discount', compute='_compute_amount_undiscounted', digits=0)
    quote_viewed = fields.Boolean('Quotation Viewed')
    require_payment = fields.Selection([
        (0, 'Online Signature'),
        (1, 'Online Payment')], default=_get_default_online_payment, string='Confirmation Mode',
        help="Choose how you want to confirm an order to launch the delivery process. You can either "
             "request a digital signature or an upfront payment. With a digital signature, you can "
             "request the payment when issuing the invoice.")

    @api.multi
    def copy(self, default=None):
        if self.template_id and self.template_id.number_of_days > 0:
            default = dict(default or {})
            default['validity_date'] = fields.Date.to_string(datetime.now() + timedelta(self.template_id.number_of_days))
        return super(SaleOrder, self).copy(default=default)

    @api.one
    def _compute_amount_undiscounted(self):
        total = 0.0
        for line in self.order_line:
            total += line.price_subtotal + line.price_unit * ((line.discount or 0.0) / 100.0) * line.product_uom_qty  # why is there a discount in a field named amount_undiscounted ??
        self.amount_undiscounted = total

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        super(SaleOrder, self).onchange_partner_id()
        self.note = self.template_id.note or self.note

    @api.onchange('partner_id')
    def onchange_update_description_lang(self):
        if not self.template_id:
            return
        else:
            template = self.template_id.with_context(lang=self.partner_id.lang)
            self.website_description = template.website_description

    @api.onchange('template_id')
    def onchange_template_id(self):
        if not self.template_id:
            return
        template = self.template_id.with_context(lang=self.partner_id.lang)

        order_lines = [(5, 0, 0)]
        for line in template.quote_line:
            discount = 0
            if self.pricelist_id:
                price = self.pricelist_id.with_context(uom=line.product_uom_id.id).get_product_price(line.product_id, line.product_uom_qty, False)
                if self.pricelist_id.discount_policy == 'without_discount' and line.price_unit:
                    discount = (line.price_unit - price) / line.price_unit * 100
                    # negative discounts (= surcharge) are included in the display price
                    if discount < 0:
                        discount = 0
                    else:
                        price = line.price_unit

            else:
                price = line.price_unit

            data = {
                'name': line.name,
                'price_unit': price,
                'discount': 100 - ((100 - discount) * (100 - line.discount)/100),
                'product_uom_qty': line.product_uom_qty,
                'product_id': line.product_id.id,
                'layout_category_id': line.layout_category_id,
                'product_uom': line.product_uom_id.id,
                'website_description': line.website_description,
                'state': 'draft',
                'customer_lead': self._get_customer_lead(line.product_id.product_tmpl_id),
            }
            if self.pricelist_id:
                data.update(self.env['sale.order.line']._get_purchase_price(self.pricelist_id, line.product_id, line.product_uom_id, fields.Date.context_today(self)))
            order_lines.append((0, 0, data))

        self.order_line = order_lines
        self.order_line._compute_tax_id()

        option_lines = []
        for option in template.options:
            if self.pricelist_id:
                price = self.pricelist_id.with_context(uom=option.uom_id.id).get_product_price(option.product_id, 1, False)
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

        if template.number_of_days > 0:
            self.validity_date = fields.Date.to_string(datetime.now() + timedelta(template.number_of_days))

        self.website_description = template.website_description
        self.require_payment = template.require_payment

        if template.note:
            self.note = template.note

    @api.multi
    def open_quotation(self):
        self.ensure_one()
        self.write({'quote_viewed': True})
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '/quote/%s/%s' % (self.id, self.access_token)
        }

    @api.multi
    def get_access_action(self, access_uid=None):
        """ Instead of the classic form view, redirect to the online quote if it exists. """
        self.ensure_one()
        user = access_uid and self.env['res.users'].sudo().browse(access_uid) or self.env.user

        if not self.template_id or (not user.share and not self.env.context.get('force_website')):
            return super(SaleOrder, self).get_access_action(access_uid)
        return {
            'type': 'ir.actions.act_url',
            'url': '/quote/%s/%s' % (self.id, self.access_token),
            'target': 'self',
            'res_id': self.id,
        }

    def get_mail_url(self):
        self.ensure_one()
        if self.state not in ['sale', 'done']:
            auth_param = url_encode(self.partner_id.signup_get_auth_param()[self.partner_id.id])
            return '/quote/%s/%s?' % (self.id, self.access_token) + auth_param
        return super(SaleOrder, self).get_mail_url()

    def get_portal_confirmation_action(self):
        """ Template override default behavior of pay / sign chosen in sales settings """
        if self.require_payment is not None or self.require_payment is not False:
            return 'pay' if self.require_payment == 1 else 'sign'
        return super(SaleOrder, self).get_portal_confirmation_action()

    @api.multi
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            if order.template_id and order.template_id.mail_template_id:
                self.template_id.mail_template_id.send_mail(order.id)
        return res

    @api.multi
    def _get_payment_type(self):
        self.ensure_one()
        return 'form_save' if self.require_payment else 'form'


class SaleOrderOption(models.Model):
    _name = "sale.order.option"
    _description = "Sale Options"
    _order = 'sequence, id'

    order_id = fields.Many2one('sale.order', 'Sales Order Reference', ondelete='cascade', index=True)
    line_id = fields.Many2one('sale.order.line', on_delete="set null")
    name = fields.Text('Description', required=True)
    product_id = fields.Many2one('product.product', 'Product', domain=[('sale_ok', '=', True)])
    layout_category_id = fields.Many2one('sale.layout_category', string='Section')
    website_description = fields.Html('Line Description', sanitize_attributes=False, translate=html_translate)
    price_unit = fields.Float('Unit Price', required=True, digits=dp.get_precision('Product Price'))
    discount = fields.Float('Discount (%)', digits=dp.get_precision('Discount'))
    uom_id = fields.Many2one('product.uom', 'Unit of Measure ', required=True)
    quantity = fields.Float('Quantity', required=True, digits=dp.get_precision('Product UoS'), default=1)
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
            self.price_unit = pricelist.with_context(uom=self.uom_id.id).get_product_price(product, self.quantity, partner_id)
        domain = {'uom_id': [('category_id', '=', self.product_id.uom_id.category_id.id)]}
        return {'domain': domain}

    @api.multi
    def button_add_to_order(self):
        self.ensure_one()
        order = self.order_id
        if order.state not in ['draft', 'sent']:
            return False

        order_line = order.order_line.filtered(lambda line: line.product_id == self.product_id)
        if order_line:
            order_line = order_line[0]
            order_line.product_uom_qty += self.quantity
        else:
            vals = {
                'price_unit': self.price_unit,
                'website_description': self.website_description,
                'name': self.name,
                'order_id': order.id,
                'product_id': self.product_id.id,
                'layout_category_id': self.layout_category_id.id,
                'product_uom_qty': self.quantity,
                'product_uom': self.uom_id.id,
                'discount': self.discount,
            }
            order_line = self.env['sale.order.line'].create(vals)
            order_line._compute_tax_id()

        self.write({'line_id': order_line.id})
        return {'type': 'ir.actions.client', 'tag': 'reload'}
