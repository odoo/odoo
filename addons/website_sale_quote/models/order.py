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
import hashlib
import time

class sale_order_line(osv.osv):
    _inherit = "sale.order.line"
    _description = "Sales Order Line"
    _columns = {
        'website_description':fields.html('Line Description'),
    }

    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,uom=False, qty_uos=0, uos=False, name='', partner_id=False,lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, context=None):
        res = super(sale_order_line, self).product_id_change(cr, uid, ids, pricelist, product, qty,uom, qty_uos, uos, name, partner_id,lang, update_tax, date_order, packaging, fiscal_position, flag, context)
        if product:
            desc = self.pool.get('product.product').browse(cr, uid, product, context).website_description
            res.get('value').update({'website_description': desc})
        print res
        return res

class sale_order(osv.osv):
    _inherit = 'sale.order'
    _columns = {
        'quote_url': fields.char('URL'),
        'access_token':fields.char('Quotation Token', size=256),
        'template_id': fields.many2one('sale.order','Quote Template'),
        'website_description': fields.html('Description'),
        'is_template': fields.boolean('Is Template'),
    }

    def new_quotation_token(self, cr, uid, record_id,context=None):
        db_uuid = self.pool.get('ir.config_parameter').get_param(cr, uid, 'database.uuid')
        quotation_token = hashlib.sha256('%s-%s-%s' % (time.time(), db_uuid, record_id)).hexdigest()
        return self.write(cr, uid, [record_id],{'access_token': quotation_token,'quote_url': self.get_signup_url(cr, uid, quotation_token, context)} )

    def create(self, cr, uid, vals, context=None):
        template_id = vals.get('template_id', False)
        new_id = super(sale_order, self).create(cr, uid, vals, context=context)
        self.new_quotation_token(cr, uid, new_id,context)
        return new_id

    def get_signup_url(self, cr, uid, token, context=None):
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url', default='http://localhost:8069', context=context)
        url = "%s/quote/%s" % (base_url ,token)
        return url

    def _get_sale_order_line(self, cr, uid,template_id, context=None):
        line_pool = self.pool.get('sale.order.line')
        lines = []
        order_template = self.browse(cr, uid, template_id, context)
        for line in order_template.order_line:
            lines.append((0,0,{
            'name': line.name,
            'sequence': line.sequence,
            'price_unit': line.price_unit,
            'product_uom_qty': line.product_uom_qty,
            'discount': line.discount,
            'product_id': line.product_id.id,
            'tax_id': [(6, 0, [x.id for x in line.tax_id])],
            'website_description':line.website_description,
            }))
        return {'order_line':lines,'website_description': order_template.website_description}

    def onchange_template_id(self, cr, uid,ids, template_id, context=None):
        data = self._get_sale_order_line(cr, uid, template_id, context)
        return {'value':data}
