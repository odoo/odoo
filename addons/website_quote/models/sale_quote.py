# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp.osv import osv, fields
import openerp.addons.decimal_precision as dp

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
