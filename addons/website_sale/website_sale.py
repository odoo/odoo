# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C)-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version of the
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

from openerp import SUPERUSER_ID
from openerp.osv import osv, fields


class product_pricelist(osv.osv):
    _inherit = "product.pricelist"
    _columns = {
        'code': fields.char('Promotionnal Code', size=64, translate=True),
    }

class product_template(osv.osv):
    _inherit = "product.template"
    _order = 'website_published,name'
    _columns = {
        'website_published': fields.boolean('Available in the website'),
        'website_description': fields.html('Description for the website'),
        'suggested_product_id': fields.many2one('product.template', 'Suggested For Product'),
        'suggested_product_ids': fields.one2many('product.template', 'suggested_product_id', 'Suggested Products'),
        'website_sizex': fields.selection(map(lambda x: (str(x+1),str(x+1)), range(12)), 'Size X'),
        'website_sizey': fields.selection(map(lambda x: (str(x+1),str(x+1)), range(6)), 'Size Y'),
        'website_product_class': fields.selection([('','Default'), ('oe_image_full','Image Full')], 'Size Y'),
    }
    _defaults = {
        'website_sizex': '3',
        'website_sizey': '2',
        'website_product_class': '',
    }

    def recommended_products(self, cr, uid, ids, context=None):
        id = ids[0]
        product_ids = []
        query = """
            SELECT      sol.product_id
            FROM        sale_order_line as my
            LEFT JOIN   sale_order_line as sol
            ON          sol.order_id = my.order_id
            WHERE       my.product_id in (%s)
            AND         sol.product_id not in (%s)
            GROUP BY    sol.product_id
            ORDER BY    COUNT(sol.order_id) DESC
            LIMIT 10
        """
        cr.execute(query, (id, id))
        for p in cr.fetchall():
            product_ids.append(p[0])

        # search to apply access rules
        product_ids = self.search(cr, uid, [("id", "in", product_ids)], limit=3)
        return self.browse(cr, uid, product_ids)

    def img(self, cr, uid, ids, field='image_small', context=None):
        return "/website/image?model=%s&field=%s&id=%s" % (self._name, field, ids[0])

class product_product(osv.osv):
    _inherit = "product.product"
    
    def _website_url(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        for id in ids:
            res[id] = "%s/shop/product/%s/" % (base_url, id)
        return res

    _columns = {
        'website_url': fields.function(_website_url, string="Website url"),
    }
    
    def img(self, cr, uid, ids, field='image_small', context=None):
        return "/website/image?model=%s&field=%s&id=%s" % (self._name, field, ids[0])

class sale_order(osv.osv):
    _inherit = "sale.order"
 
    def get_total_quantity(self, cr, uid, ids, context=None):
        order = self.browse(cr, uid, ids[0], context=context)

        return sum(l.product_uom_qty for l in (order.order_line or []))

class sale_order_line(osv.osv):
    _inherit = "sale.order.line"
 
    def _recalculate_product_values(self, cr, uid, ids, product_id=None, context=None):
        user_obj = self.pool.get('res.users')
        product_id = product_id or ids and self.browse(cr, uid, ids[0], context=context).product_id.id
        return self.product_id_change(cr, SUPERUSER_ID, [],
            pricelist=context.pop('pricelist'),
            product=product_id,
            partner_id=user_obj.browse(cr, SUPERUSER_ID, uid).partner_id.id,
            context=context)['value']
