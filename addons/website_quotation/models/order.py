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


class sale_quote_template(osv.osv):
    _name = "sale.quote.template"
    _description = "Sale Quotation Template"
    _columns = {
        'name': fields.char('Quotation Template', size=256, required=True),
        'website_description': fields.html('Description'),
        'quote_line': fields.one2many('sale.quote.line', 'quote_id', 'Quote Template Lines'),
        'note': fields.text('Terms and conditions'),
        'options': fields.one2many('sale.option.line', 'temp_option_id', 'Optional Products Lines'),
    }

    def open_template(self, cr, uid, quote_id, context=None):
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '/template/%d' % quote_id[0]
        }


class sale_quote_line(osv.osv):
    _name = "sale.quote.line"
    _description = "Quotation Template Lines"
    _columns = {
        'quote_id': fields.many2one('sale.quote.template', 'Quotation Template Reference', required=True, ondelete='cascade', select=True),
        'name': fields.text('Description', required=True),
        'product_id': fields.many2one('product.product', 'Product', domain=[('sale_ok', '=', True)], change_default=True),
        'website_description': fields.html('Line Description'),
        'price_unit': fields.float('Unit Price', required=True),
        'product_uom_qty': fields.float('Quantity', required=True),
    }
    _defaults = {
        'product_uom_qty': 1,
    }
    def on_change_product_id(self, cr, uid, ids, product, context=None):
        vals = {}
        product_obj = self.pool.get('product.product').browse(cr, uid, product, context=context)
        vals.update({
            'price_unit': product_obj.list_price,
            'website_description': product_obj.website_description,
            'name': product_obj.name,
        })
        return {'value': vals}


class sale_order_line(osv.osv):
    _inherit = "sale.order.line"
    _description = "Sales Order Line"
    _columns = {
        'website_description': fields.html('Line Description'),
        'is_optional': fields.boolean('Optional Product')
    }
    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0, uom=False, qty_uos=0, uos=False, name='', partner_id=False, lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, context=None):
        res = super(sale_order_line, self).product_id_change(cr, uid, ids, pricelist, product, qty, uom, qty_uos, uos, name, partner_id, lang, update_tax, date_order, packaging, fiscal_position, flag, context)
        if product:
            desc = self.pool.get('product.product').browse(cr, uid, product, context).website_description
            res.get('value').update({'website_description': desc})
        return res


class sale_order(osv.osv):
    _inherit = 'sale.order'
    _columns = {
        'access_token': fields.char('Security Token', size=256, required=True),
        'template_id': fields.many2one('sale.quote.template', 'Quote Template'),
        'website_description': fields.html('Description'),
        'options' : fields.one2many('sale.option.line', 'option_id', 'Optional Products Lines'),
        'signer_name': fields.char('Signer Name', size=256),
    }
    _defaults = {
        'access_token': lambda self, cr, uid, ctx={}: str(uuid.uuid4())
    }
    def open_quotation(self, cr, uid, quote_id, context=None):
        quote = self.browse(cr, uid, quote_id[0], context=context)
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '/quote/%s/%s' % (quote.id, quote.access_token)
        }

    def _get_sale_order_line(self, cr, uid, template_id, context=None):
        """create order line from selected quote template line."""

    def onchange_template_id(self, cr, uid, ids, template_id, context=None):
        lines = []
        quote_template = self.pool.get('sale.quote.template').browse(cr, uid, template_id, context=context)
        for line in quote_template.quote_line:
            lines.append((0, 0, {
                'name': line.name,
                'price_unit': line.price_unit,
                'product_uom_qty': line.product_uom_qty,
                'product_id': line.product_id.id,
                'product_uom_id': line.product_id.uom_id.id,
                'website_description': line.website_description,
                'state': 'draft',
            }))
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
        data = {'order_line': lines, 'website_description': quote_template.website_description, 'note': quote_template.note, 'options': options}
        return {'value': data}

    def recommended_products(self, cr, uid, ids, context=None):
        order_line = self.browse(cr, uid, ids[0], context=context).order_line
        product_pool = self.pool.get('product.product')
        products = []
        for line in order_line:
            products += line.product_id.product_tmpl_id.recommended_products(context=context)
        return products
        
class sale_option_line(osv.osv):
    _name = "sale.option.line"
    _description = "Sale Options"
    _columns = {
        'option_id': fields.many2one('sale.order', 'Sale Order Reference', ondelete='cascade', select=True),
        'temp_option_id': fields.many2one('sale.quote.template', 'Quotation Template Reference', ondelete='cascade', select=True),
        'line_id': fields.many2one('sale.order.line', on_delete="set null"),
        'name': fields.text('Description', required=True),
        'product_id': fields.many2one('product.product', 'Product', domain=[('sale_ok', '=', True)], change_default=True),
        'website_description': fields.html('Line Description'),
        'price_unit': fields.float('Unit Price', required=True),
        'discount': fields.float('Discount (%)'),
        'uom_id': fields.many2one('product.uom', 'Unit of Measure ', required=True),
        'quantity': fields.float('Quantity', required=True),
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
