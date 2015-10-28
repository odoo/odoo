# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api
from openerp.osv import osv, fields
import uuid
import time
import datetime

import openerp.addons.decimal_precision as dp
from openerp import SUPERUSER_ID
from openerp.tools.translate import _


class sale_quote_template(osv.osv):
    _name = "sale.quote.template"
    _description = "Sale Quotation Template"
    _columns = {
        'name': fields.char('Quotation Template', required=True),
        'website_description': fields.html('Description', translate=True),
        'quote_line': fields.one2many('sale.quote.line', 'quote_id', 'Quotation Template Lines', copy=True),
        'note': fields.text('Terms and conditions'),
        'options': fields.one2many('sale.quote.option', 'template_id', 'Optional Products Lines', copy=True),
        'number_of_days': fields.integer('Quotation Duration', help='Number of days for the validity date computation of the quotation'),
        'require_payment': fields.selection([
            (0, 'Not mandatory on website quote validation'),
            (1, 'Immediate after website order validation')
            ], 'Payment', help="Require immediate payment by the customer when validating the order from the website quote"),
    }
    def open_template(self, cr, uid, quote_id, context=None):
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '/quote/template/%d' % quote_id[0]
        }

class sale_quote_line(osv.osv):
    _name = "sale.quote.line"
    _description = "Quotation Template Lines"
    _columns = {
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of sale quote lines."),
        'quote_id': fields.many2one('sale.quote.template', 'Quotation Template Reference', required=True, ondelete='cascade', select=True),
        'name': fields.text('Description', required=True, translate=True),
        'product_id': fields.many2one('product.product', 'Product', domain=[('sale_ok', '=', True)], required=True),
        'website_description': fields.related('product_id', 'product_tmpl_id', 'quote_description', string='Line Description', type='html', translate=True),
        'price_unit': fields.float('Unit Price', required=True, digits_compute= dp.get_precision('Product Price')),
        'discount': fields.float('Discount (%)', digits_compute= dp.get_precision('Discount')),
        'product_uom_qty': fields.float('Quantity', required=True, digits_compute= dp.get_precision('Product UoS')),
        'product_uom_id': fields.many2one('product.uom', 'Unit of Measure ', required=True),
    }
    _order = 'sequence, id'
    _defaults = {
        'product_uom_qty': 1,
        'discount': 0.0,
        'sequence': 10,
    }
    def on_change_product_id(self, cr, uid, ids, product, uom_id=None, context=None):
        vals, domain = {}, []
        product_obj = self.pool.get('product.product').browse(cr, uid, product, context=context)
        name = product_obj.name
        if product_obj.description_sale:
            name += '\n' + product_obj.description_sale
        vals.update({
            'price_unit': product_obj.lst_price,
            'product_uom_id': product_obj.uom_id.id,
            'website_description': product_obj and (product_obj.quote_description or product_obj.website_description) or '',
            'name': name,
            'product_uom_id': uom_id or product_obj.uom_id.id,
        })
        uom_obj = self.pool.get('product.uom')
        if vals['product_uom_id'] != product_obj.uom_id.id:
            selected_uom = uom_obj.browse(cr, uid, vals['product_uom_id'], context=context)
            new_price = uom_obj._compute_price(cr, uid, product_obj.uom_id.id, vals['price_unit'], vals['product_uom_id'])
            vals['price_unit'] = new_price
        if not uom_id:
            domain = {'product_uom_id': [('category_id', '=', product_obj.uom_id.category_id.id)]}
        return {'value': vals, 'domain': domain}

    def product_uom_change(self, cr, uid, ids, product, uom_id, context=None):
        context = context or {}
        if not uom_id:
            return {'value': {'price_unit': 0.0, 'uom_id': False}}
        return self.on_change_product_id(cr, uid, ids, product, uom_id=uom_id, context=context)

    def _inject_quote_description(self, cr, uid, values, context=None):
        values = dict(values or {})
        if not values.get('website_description') and values.get('product_id'):
            product = self.pool['product.product'].browse(cr, uid, values['product_id'], context=context)
            values['website_description'] = product.quote_description or product.website_description or ''
        return values

    def create(self, cr, uid, values, context=None):
        values = self._inject_quote_description(cr, uid, values, context)
        ret = super(sale_quote_line, self).create(cr, uid, values, context=context)
        # hack because create don t make the job for a related field
        if values.get('website_description'):
            self.write(cr, uid, ret, {'website_description': values['website_description']}, context=context)
        return ret

    def write(self, cr, uid, ids, values, context=None):
        values = self._inject_quote_description(cr, uid, values, context)
        return super(sale_quote_line, self).write(cr, uid, ids, values, context=context)


class sale_order_line(osv.osv):
    _inherit = "sale.order.line"
    _description = "Sales Order Line"
    _columns = {
        'website_description': fields.html('Line Description'),
        'option_line_id': fields.one2many('sale.order.option', 'line_id', 'Optional Products Lines'),
    }

    def _inject_quote_description(self, cr, uid, values, context=None):
        values = dict(values or {})
        if not values.get('website_description') and values.get('product_id'):
            product = self.pool['product.product'].browse(cr, uid, values['product_id'], context=context)
            values['website_description'] = product.quote_description or product.website_description
        return values

    def create(self, cr, uid, values, context=None):
        values = self._inject_quote_description(cr, uid, values, context)
        ret = super(sale_order_line, self).create(cr, uid, values, context=context)
        # hack because create don t make the job for a related field
        if values.get('website_description'):
            self.write(cr, uid, ret, {'website_description': values['website_description']}, context=context)
        return ret

    def write(self, cr, uid, ids, values, context=None):
        values = self._inject_quote_description(cr, uid, values, context)
        return super(sale_order_line, self).write(cr, uid, ids, values, context=context)


class sale_order(osv.osv):
    _inherit = 'sale.order'

    def _get_total(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            total = 0.0
            for line in order.order_line:
                total += line.price_subtotal + line.price_unit * ((line.discount or 0.0) / 100.0) * line.product_uom_qty
            res[order.id] = total
        return res

    _columns = {
        'access_token': fields.char('Security Token', required=True, copy=False),
        'template_id': fields.many2one('sale.quote.template', 'Quotation Template', readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}),
        'website_description': fields.html('Description'),
        'options' : fields.one2many('sale.order.option', 'order_id', 'Optional Products Lines', readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, copy=True),
        'amount_undiscounted': fields.function(_get_total, string='Amount Before Discount', type="float", digits=0),
        'quote_viewed': fields.boolean('Quotation Viewed'),
        'require_payment': fields.selection([
            (0, 'Not mandatory on website quote validation'),
            (1, 'Immediate after website order validation')
            ], 'Payment', help="Require immediate payment by the customer when validating the order from the website quote"),
    }

    def _get_template_id(self, cr, uid, context=None):
        try:
            template_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'website_quote', 'website_quote_template_default')[1]
        except ValueError:
            template_id = False
        return template_id

    _defaults = {
        'access_token': lambda self, cr, uid, ctx={}: str(uuid.uuid4()),
        'template_id' : _get_template_id,
    }

    def open_quotation(self, cr, uid, quote_id, context=None):
        quote = self.browse(cr, uid, quote_id[0], context=context)
        self.write(cr, uid, quote_id[0], {'quote_viewed': True}, context=context)
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '/quote/%s/%s' % (quote.id, quote.access_token)
        }

    def onchange_template_id(self, cr, uid, ids, template_id, partner=False, fiscal_position_id=False, pricelist_id=False, context=None):
        if not template_id:
            return {}

        if partner:
            context = dict(context or {})
            context['lang'] = self.pool['res.partner'].browse(cr, uid, partner, context).lang

        pricelist_obj = self.pool['product.pricelist']

        lines = [(5,)]
        quote_template = self.pool.get('sale.quote.template').browse(cr, uid, template_id, context=context)
        for line in quote_template.quote_line:
            res = self.pool.get('sale.order.line').product_id_change(cr, uid, False,
                False, line.product_id.id, line.product_uom_qty, line.product_uom_id.id, line.product_uom_qty,
                line.product_uom_id.id, line.name, partner, False, True, time.strftime('%Y-%m-%d'),
                False, fiscal_position_id, True, context)
            data = res.get('value', {})
            if pricelist_id:
                uom_context = context.copy()
                uom_context['uom'] = line.product_uom_id.id
                price = pricelist_obj.price_get(cr, uid, [pricelist_id], line.product_id.id, 1, context=uom_context)[pricelist_id]
            else:
                price = line.price_unit

            if 'tax_id' in data:
                data['tax_id'] = [(6, 0, data['tax_id'])]
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
            if pricelist_id:
                uom_context = context.copy()
                uom_context['uom'] = option.uom_id.id
                price = pricelist_obj.price_get(cr, uid, [pricelist_id], option.product_id.id, 1, context=uom_context)[pricelist_id]
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
            date = (datetime.datetime.now() + datetime.timedelta(quote_template.number_of_days)).strftime("%Y-%m-%d")
        data = {
            'order_line': lines,
            'website_description': quote_template.website_description,
            'options': options,
            'validity_date': date,
            'require_payment': quote_template.require_payment
        }
        if quote_template.note:
            data['note'] = quote_template.note
        return {'value': data}

    def recommended_products(self, cr, uid, ids, context=None):
        order_line = self.browse(cr, uid, ids[0], context=context).order_line
        product_pool = self.pool.get('product.product')
        products = []
        for line in order_line:
            products += line.product_id.product_tmpl_id.recommended_products(context=context)
        return products

    def get_access_action(self, cr, uid, id, context=None):
        """ Override method that generated the link to access the document. Instead
        of the classic form view, redirect to the online quote if exists. """
        quote = self.browse(cr, uid, id, context=context)
        if not quote.template_id:
            return super(sale_order, self).get_access_action(cr, uid, id, context=context)
        return {
            'type': 'ir.actions.act_url',
            'url': '/quote/%s' % id,
            'target': 'self',
            'res_id': id,
        }

    def _confirm_online_quote(self, cr, uid, order_id, tx, context=None):
        """ Payment callback: validate the order and write tx details in chatter """
        order = self.browse(cr, uid, order_id, context=context)

        # create draft invoice if transaction is ok
        if tx and tx.state == 'done':
            if order.state in ['draft', 'sent']:
                self.signal_workflow(cr, SUPERUSER_ID, [order.id], 'manual_invoice', context=context)
            message = _('Order payed by %s. Transaction: %s. Amount: %s.') % (tx.partner_id.name, tx.acquirer_reference, tx.amount)
            self.message_post(cr, uid, order_id, body=message, type='comment', subtype='mt_comment', context=context)
            return True
        return False

    def create(self, cr, uid, values, context=None):
        if not values.get('template_id'):
            defaults = self.default_get(cr, uid, ['template_id'], context=context)
            template_values = self.onchange_template_id(cr, uid, [], defaults.get('template_id'), partner=values.get('partner_id'), fiscal_position_id=values.get('fiscal_position'), context=context).get('value', {})
            values = dict(template_values, **values)
        return super(sale_order, self).create(cr, uid, values, context=context)


class sale_quote_option(osv.osv):
    _name = "sale.quote.option"
    _description = "Quotation Option"
    _columns = {
        'template_id': fields.many2one('sale.quote.template', 'Quotation Template Reference', ondelete='cascade', select=True, required=True),
        'name': fields.text('Description', required=True, translate=True),
        'product_id': fields.many2one('product.product', 'Product', domain=[('sale_ok', '=', True)], required=True),
        'website_description': fields.html('Option Description', translate=True),
        'price_unit': fields.float('Unit Price', required=True, digits_compute= dp.get_precision('Product Price')),
        'discount': fields.float('Discount (%)', digits_compute= dp.get_precision('Discount')),
        'uom_id': fields.many2one('product.uom', 'Unit of Measure ', required=True),
        'quantity': fields.float('Quantity', required=True, digits_compute= dp.get_precision('Product UoS')),
    }
    _defaults = {
        'quantity': 1,
    }

    def on_change_product_id(self, cr, uid, ids, product, uom_id=None, context=None):
        vals, domain = {}, []
        product_obj = self.pool.get('product.product').browse(cr, uid, product, context=context)
        name = product_obj.name
        if product_obj.description_sale:
            name += '\n' + product_obj.description_sale
        vals.update({
            'price_unit': product_obj.list_price,
            'website_description': product_obj.product_tmpl_id.quote_description,
            'name': name,
            'uom_id': uom_id or product_obj.uom_id.id,
        })
        uom_obj = self.pool.get('product.uom')
        if vals['uom_id'] != product_obj.uom_id.id:
            selected_uom = uom_obj.browse(cr, uid, vals['uom_id'], context=context)
            new_price = uom_obj._compute_price(cr, uid, product_obj.uom_id.id,
                                               vals['price_unit'], vals['uom_id'])
            vals['price_unit'] = new_price
        if not uom_id:
            domain = {'uom_id': [('category_id', '=', product_obj.uom_id.category_id.id)]}
        return {'value': vals, 'domain': domain}

    def product_uom_change(self, cr, uid, ids, product, uom_id, context=None):
        if not uom_id:
            return {'value': {'price_unit': 0.0, 'uom_id': False}}
        return self.on_change_product_id(cr, uid, ids, product, uom_id=uom_id, context=context)


class sale_order_option(osv.osv):
    _name = "sale.order.option"
    _description = "Sale Options"
    _columns = {
        'order_id': fields.many2one('sale.order', 'Sale Order Reference', ondelete='cascade', select=True),
        'line_id': fields.many2one('sale.order.line', on_delete="set null"),
        'name': fields.text('Description', required=True),
        'product_id': fields.many2one('product.product', 'Product', domain=[('sale_ok', '=', True)]),
        'website_description': fields.html('Line Description'),
        'price_unit': fields.float('Unit Price', required=True, digits_compute= dp.get_precision('Product Price')),
        'discount': fields.float('Discount (%)', digits_compute= dp.get_precision('Discount')),
        'uom_id': fields.many2one('product.uom', 'Unit of Measure ', required=True),
        'quantity': fields.float('Quantity', required=True,
            digits_compute= dp.get_precision('Product UoS')),
    }

    _defaults = {
        'quantity': 1,
    }

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

    def product_uom_change(self, cr, uid, ids, product, uom_id, context=None):
        context = context or {}
        if not uom_id:
            return {'value': {'price_unit': 0.0, 'uom_id': False}}
        return self.on_change_product_id(cr, uid, ids, product, uom_id=uom_id, context=context)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        product = self.product_id.with_context(lang=self.order_id.partner_id.lang)
        self.price_unit = product.list_price
        self.website_description = product.quote_description or product.website_description
        self.name = product.name
        if product.description_sale:
            self.name += '\n' + product.description_sale
        self.uom_id = product.product_tmpl_id.uom_id
        if product and self.order_id.pricelist_id:
            partner_id = self.order_id.partner_id.id
            pricelist = self.order_id.pricelist_id.id
            self.price_unit = self.order_id.pricelist_id.price_get(product.id, self.quantity, partner_id)[pricelist]


class product_template(osv.Model):
    _inherit = "product.template"

    _columns = {
        'website_description': fields.html('Description for the website'), # hack, if website_sale is not installed
        'quote_description': fields.html('Description for the quote'),
    }
