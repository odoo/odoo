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
        'website_description': fields.html('Line Description', translate=True),
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
        vals.update({
            'price_unit': product_obj.list_price,
            'product_uom_id': product_obj.uom_id.id,
            'website_description': product_obj.website_description,
            'name': product_obj.name,
        })
        return {'value': vals}


class sale_order_line(osv.osv):
    _inherit = "sale.order.line"
    _description = "Sales Order Line"
    _columns = {
        'website_description': fields.html('Line Description'),
        'option_line_id': fields.one2many('sale.order.option', 'line_id', 'Optional Products Lines'),
    }

    def _inject_website_description(self, cr, uid, values, context=None):
        values = dict(values or {})
        if not values.get('website_description') and values.get('product_id'):
            product = self.pool['product.product'].browse(cr, uid, values['product_id'], context=context)
            values['website_description'] = product.website_description
        return values

    def create(self, cr, uid, values, context=None):
        values = self._inject_website_description(cr, uid, values, context)
        return super(sale_order_line, self).create(cr, uid, values, context=context)

    def write(self, cr, uid, ids, values, context=None):
        values = self._inject_website_description(cr, uid, values, context)
        return super(sale_order_line, self).write(cr, uid, ids, values, context=context)


class sale_order(osv.osv):
    _inherit = 'sale.order'

    def _get_total(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            total = 0.0
            for line in order.order_line:
                total += (line.product_uom_qty * line.price_unit)
            res[order.id] = total
        return res

    _columns = {
        'access_token': fields.char('Security Token', required=True, copy=False),
        'template_id': fields.many2one('sale.quote.template', 'Quote Template'),
        'website_description': fields.html('Description'),
        'options' : fields.one2many('sale.order.option', 'order_id', 'Optional Products Lines'),
        'validity_date': fields.date('Validity Date'),
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
            'website_description': product_obj.product_tmpl_id.website_description,
            'name': product_obj.name,
            'uom_id': product_obj.product_tmpl_id.uom_id.id,
        })
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
    def on_change_product_id(self, cr, uid, ids, product, context=None):
        vals = {}
        product_obj = self.pool.get('product.product').browse(cr, uid, product, context=context)
        vals.update({
            'price_unit': product_obj.list_price,
            'website_description': product_obj.product_tmpl_id.website_description,
            'name': product_obj.name,
            'uom_id': product_obj.product_tmpl_id.uom_id.id,
        })
        return {'value': vals}

class product_template(osv.Model):
    _inherit = "product.template"
    _columns = {
        'website_description': fields.html('Description for the website'),
    }
