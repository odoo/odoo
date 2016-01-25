# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import uuid

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    _description = "Sales Order Line"

    website_description = fields.Html(string='Line Description')
    option_line_id = fields.One2many('sale.order.option', 'line_id', string='Optional Products Lines')

    def _inject_quote_description(self, values):
        values = dict(values or {})
        if not values.get('website_description') and values.get('product_id'):
            product = self.env['product.product'].browse(values['product_id'])
            values['website_description'] = product.quote_description or product.website_description
        return values

    @api.model
    def create(self, values):
        result = super(SaleOrderLine, self).create(self._inject_quote_description(values))
        # hack because create don t make the job for a related field
        if values.get('website_description'):
            result.write({'website_description': values['website_description']})
        return result

    @api.multi
    def write(self, values):
        return super(SaleOrderLine, self).write(self._inject_quote_description(values))

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

    access_token = fields.Char(string='Security Token', required=True, copy=False, default=lambda self: str(uuid.uuid4()))
    template_id = fields.Many2one('sale.quote.template', string='Quotation Template', readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})
    website_description = fields.Html(string='Description', translate=True)
    options = fields.One2many('sale.order.option', 'order_id', string='Optional Products Lines', readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, copy=True)
    amount_undiscounted = fields.Float(compute='_compute_amount_undiscounted', string='Amount Before Discount', digits=0)
    quote_viewed = fields.Boolean(string='Quotation Viewed')
    require_payment = fields.Selection([
        (0, 'Not mandatory on website quote validation'),
        (1, 'Immediate after website order validation')
        ], 'Payment', help="Require immediate payment by the customer when validating the order from the website quote")

    def _compute_amount_undiscounted(self):
        for order in self:
            total = sum(line.price_subtotal + line.price_unit * ((line.discount or 0.0) / 100.0) * line.product_uom_qty for line in order.order_line)
            order.amount_undiscounted = total

    @api.multi
    def action_open_quotation(self):
        self.ensure_one()
        self.quote_viewed = True
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '/quote/%s/%s' % (self.id, self.access_token)
        }

    @api.onchange('template_id')
    def onchange_template_id(self):
        if not self.template_id:
            return {}
        ctx = dict(self.env.context)
        if self.partner_id:
            ctx.update({'lang': self.partner_id.lang})

        lines = [(5,)]
        quote_template = self.template_id.with_context(ctx)
        for line in quote_template.quote_line:
            result = self.env['sale.order.line'].with_context(ctx).product_id_change()
            data = result.get('value', {})
            if self.pricelist_id:
                ctx.update({'uom': line.product_uom_id.id})
                price = self.pricelist_id.price_get(line.product_id.id, 1)[1]
            else:
                price = line.price_unit
            if 'tax_id' in data:
                data['tax_id'] = [(6, 0, data['tax_id'])]
            else:
                fpos = (self.fiscal_position_id and self.pool['account.fiscal.position'].browse(self.fiscal_position_id)) or False
                taxes = fpos.map_tax(line.product_id.product_tmpl_id.taxes_id).ids if fpos else line.product_id.product_tmpl_id.taxes_id.ids
                data['tax_id'] = [(6, 0, taxes)]
            data.update({
                'name': line.name,
                'price_unit': price,
                'discount': line.discount,
                'product_uom_qty': line.product_uom_qty,
                'product_id': line.product_id.id,
                'product_uom': line.product_uom_id.id,
                'website_description': line.website_description,
                'state': 'draft',
            })
            lines.append((0, 0, data))
        options = []
        for option in quote_template.options:
            if self.pricelist_id:
                ctx.update({'uom': option.uom_id.id})
                price = self.pricelist_id.price_get(option.product_id.id, 1)[1]
            else:
                price = option.price_unit
            options.append((0, 0, {
                'product_id': option.product_id.id,
                'name': option.name,
                'quantity': option.quantity,
                'uom_id': option.uom_id.id,
                'price_unit': price,
                'discount': option.discount,
                'website_description': option.website_description,
            }))
        date = False
        if quote_template.number_of_days > 0:
            date = fields.Date.to_string(datetime.datetime.now() + datetime.timedelta(quote_template.number_of_days))

        self.order_line = lines
        self.website_description = quote_template.website_description
        self.note = quote_template.note
        self.options = options
        self.validity_date = date
        self.require_payment = quote_template.require_payment

    def recommended_products(self):
        order_line = self.browse(self.order_line)
        products = []
        for line in order_line:
            products += line.product_id.product_tmpl_id.recommended_products()
        return products

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

    def _confirm_online_quote(self, order_id, tx):
        """ Payment callback: validate the order and write tx details in chatter """
        order = self.browse(order_id)

        # create draft invoice if transaction is ok
        if tx and tx.state == 'done':
            if order.state in ['draft', 'sent']:
                order.signal_workflow('manual_invoice')
            message = _('Order payed by %s. Transaction: %s. Amount: %s.') % (tx.partner_id.name, tx.acquirer_reference, tx.amount)
            order.message_post(body=message, type='comment', subtype='mt_comment')
            return True
        return False

    def create(self, cr, uid, values, context=None):
        if not values.get('template_id'):
            defaults = self.default_get(cr, uid, ['template_id'], context=context)
            template_values = self.onchange_template_id(cr, uid, [], defaults.get('template_id'), partner=values.get('partner_id'), fiscal_position_id=values.get('fiscal_position'), context=context).get('value', {})
            values = dict(template_values, **values)
        return super(sale_order, self).create(cr, uid, values, context=context)

    @api.multi
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            if order.template_id and order.template_id.mail_template_id:
                order.template_id.mail_template_id.send_mail(order.id)
        return res


class SaleOrderOption(models.Model):
    _name = "sale.order.option"
    _description = "Sale Options"

    order_id = fields.Many2one('sale.order', string='Sale Order Reference', ondelete='cascade', select=True)
    line_id = fields.Many2one('sale.order.line', on_delete="set null")
    name = fields.Text(string='Description', required=True)
    product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)])
    website_description = fields.Html(string='Line Description')
    price_unit = fields.Float(string='Unit Price', required=True, digits_compute= dp.get_precision('Product Price'))
    discount = fields.Float(string='Discount (%)', digits_compute= dp.get_precision('Discount'))
    uom_id = fields.Many2one('product.uom', string='Unit of Measure ', required=True)
    quantity = fields.Float(string='Quantity', required=True,
        digits_compute= dp.get_precision('Product UoS'), default=1)

    # TODO master: to remove, replaced by onchange of the new api
    def on_change_product_id(self, cr, uid, ids, product, uom_id=None, context=None):
        vals, domain = {}, []
        if not product:
            return vals
        product_obj = self.pool.get('product.product').browse(cr, uid, product, context=context)
        name = product_obj.name
        if product_obj.description_sale:
            name += '\n'+product_obj.description_sale
        vals.update({
            'price_unit': product_obj.list_price,
            'website_description': product_obj and (product_obj.quote_description or product_obj.website_description),
            'name': name,
            'uom_id': uom_id or product_obj.uom_id.id,
        })
        uom_obj = self.pool.get('product.uom')
        if vals['uom_id'] != product_obj.uom_id.id:
            selected_uom = uom_obj.browse(cr, uid, vals['uom_id'], context=context)
            new_price = uom_obj._compute_price(cr, uid, product_obj.uom_id.id, vals['price_unit'], vals['uom_id'])
            vals['price_unit'] = new_price
        if not uom_id:
            domain = {'uom_id': [('category_id', '=', product_obj.uom_id.category_id.id)]}
        return {'value': vals, 'domain': domain}

    # TODO master: to remove, replaced by onchange of the new api
    def product_uom_change(self, cr, uid, ids, product, uom_id, context=None):
        context = context or {}
        if not uom_id:
            return {'value': {'price_unit': 0.0, 'uom_id': False}}
        return self.on_change_product_id(cr, uid, ids, product, uom_id=uom_id, context=context)

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
