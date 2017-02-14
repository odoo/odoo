# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import api
from openerp.osv import osv, fields
import uuid
import time
import datetime

import openerp.addons.decimal_precision as dp

class sale_quote_template(osv.osv):
    _name = "sale.quote.template"
    _description = "Sale Quotation Template"
    _columns = {
        'name': fields.char('Quotation Template', required=True),
        'website_description': fields.html('Description', translate=True),
        'quote_line': fields.one2many('sale.quote.line', 'quote_id', 'Quote Template Lines', copy=True),
        'note': fields.text('Terms and conditions'),
        'options': fields.one2many('sale.quote.option', 'template_id', 'Optional Products Lines', copy=True),
        'number_of_days': fields.integer('Quote Duration', help='Number of days for the validaty date computation of the quotation'),
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
        'quote_id': fields.many2one('sale.quote.template', 'Quotation Template Reference', required=True, ondelete='cascade', select=True),
        'name': fields.text('Description', required=True, translate=True),
        'product_id': fields.many2one('product.product', 'Product', domain=[('sale_ok', '=', True)], required=True),
        'website_description': fields.related('product_id', 'product_tmpl_id', 'quote_description', string='Line Description', type='html', translate=True),
        'price_unit': fields.float('Unit Price', required=True, digits_compute= dp.get_precision('Product Price')),
        'discount': fields.float('Discount (%)', digits_compute= dp.get_precision('Discount')),
        'product_uom_qty': fields.float('Quantity', required=True, digits_compute= dp.get_precision('Product UoS')),
        'product_uom_id': fields.many2one('product.uom', 'Unit of Measure ', required=True),
    }
    _defaults = {
        'product_uom_qty': 1,
        'discount': 0.0,
    }
    def on_change_product_id(self, cr, uid, ids, product, context=None):
        vals = {}
        product_obj = self.pool.get('product.product').browse(cr, uid, product, context=context)
        name = product_obj.name
        if product_obj.description_sale:
            name += '\n' + product_obj.description_sale
        vals.update({
            'price_unit': product_obj.lst_price,
            'product_uom_id': product_obj.uom_id.id,
            'website_description': product_obj and (product_obj.quote_description or product_obj.website_description) or '',
            'name': name,
        })
        return {'value': vals}

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
        'template_id': fields.many2one('sale.quote.template', 'Quote Template', readonly=True,
            states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}),
        'website_description': fields.html('Description'),
        'options' : fields.one2many('sale.order.option', 'order_id', 'Optional Products Lines', copy=True),
        'validity_date': fields.date('Expiry Date'),
        'amount_undiscounted': fields.function(_get_total, string='Amount Before Discount', type="float",
            digits_compute=dp.get_precision('Account'))
    }
    _defaults = {
        'access_token': lambda self, cr, uid, ctx={}: str(uuid.uuid4())
    }

    def open_quotation(self, cr, uid, quote_id, context=None):
        quote = self.browse(cr, uid, quote_id[0], context=context)
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '/quote/%s' % (quote.id)
        }

    def onchange_template_id(self, cr, uid, ids, template_id, partner=False, fiscal_position=False, context=None):
        if not template_id:
            return True

        if context is None:
            context = {}
        context = dict(context, lang=self.pool.get('res.partner').browse(cr, uid, partner, context).lang)
        
        lines = [(5,)]
        quote_template = self.pool.get('sale.quote.template').browse(cr, uid, template_id, context=context)
        for line in quote_template.quote_line:
            res = self.pool.get('sale.order.line').product_id_change(cr, uid, False,
                False, line.product_id.id, line.product_uom_qty, line.product_uom_id.id, line.product_uom_qty,
                line.product_uom_id.id, line.name, partner, False, True, time.strftime('%Y-%m-%d'),
                False, fiscal_position, True, context)
            data = res.get('value', {})
            if 'tax_id' in data:
                data['tax_id'] = [(6, 0, data['tax_id'])]
            data.update({
                'name': line.name,
                'price_unit': line.price_unit,
                'discount': line.discount,
                'product_uom_qty': line.product_uom_qty,
                'product_id': line.product_id.id,
                'product_uom': line.product_uom_id.id,
                'website_description': line.website_description,
                'state': 'draft',
                'delay': self.pool['sale.order']._get_customer_lead(cr, uid, line.product_id.product_tmpl_id)
            })
            lines.append((0, 0, data))
        options = []
        for option in quote_template.options:
            options.append((0, 0, {
                'product_id': option.product_id.id,
                'name': option.name,
                'quantity': option.quantity,
                'uom_id': option.uom_id.id,
                'price_unit': option.price_unit,
                'discount': option.discount,
                'website_description': option.website_description,
            }))
        date = False
        if quote_template.number_of_days > 0:
            date = (datetime.datetime.now() + datetime.timedelta(quote_template.number_of_days)).strftime("%Y-%m-%d")
        data = {'order_line': lines, 'website_description': quote_template.website_description, 'note': quote_template.note, 'options': options, 'validity_date': date}
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

    def action_quotation_send(self, cr, uid, ids, context=None):
        action = super(sale_order, self).action_quotation_send(cr, uid, ids, context=context)
        ir_model_data = self.pool.get('ir.model.data')
        quote_template_id = self.read(cr, uid, ids, ['template_id'], context=context)[0]['template_id']
        if quote_template_id:
            try:
                template_id = ir_model_data.get_object_reference(cr, uid, 'website_quote', 'email_template_edi_sale')[1]
            except ValueError:
                pass
            else:
                action['context'].update({
                    'default_template_id': template_id,
                    'default_use_template': True
                })

        return action


class sale_quote_option(osv.osv):
    _name = "sale.quote.option"
    _description = "Quote Option"
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
    def on_change_product_id(self, cr, uid, ids, product, context=None):
        vals = {}
        product_obj = self.pool.get('product.product').browse(cr, uid, product, context=context)
        vals.update({
            'price_unit': product_obj.list_price,
            'website_description': product_obj.product_tmpl_id.quote_description,
            'name': product_obj.name,
            'uom_id': product_obj.product_tmpl_id.uom_id.id,
        })
        if product_obj.description_sale:
            vals['name'] += '\n'+product_obj.description_sale
        return {'value': vals}

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
    def on_change_product_id(self, cr, uid, ids, product, context=None):
        vals = {}
        if not product:
            return vals
        product_obj = self.pool.get('product.product').browse(cr, uid, product, context=context)
        vals.update({
            'price_unit': product_obj.list_price,
            'website_description': product_obj and (product_obj.quote_description or product_obj.website_description),
            'name': product_obj.name,
            'uom_id': product_obj.product_tmpl_id.uom_id.id,
        })
        if product_obj.description_sale:
            vals['name'] += '\n'+product_obj.description_sale
        return {'value': vals}

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

