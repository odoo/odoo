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


class product_pricelist(osv.Model):
    _inherit = "product.pricelist"
    _columns = {
        'code': fields.char('Promotionnal Code', size=64, translate=True),
    }


class product_template(osv.Model):
    _inherit = ["product.template", "website.seo.metadata"]
    _order = 'website_published desc, website_sequence desc, name'
    _name = 'product.template'

    def _website_url(self, cr, uid, ids, field_name, arg, context=None):
        """ TDE-NOTE: as someone wrote this method without any clue on about what it
        does, fixing bugs about product_variant_ids not existing will be done
        based on the weather, the sun and Lilo's feelings about pigs.

        If you see this comment in trunk, this means that the website branch has
        been merged without any review, which is quite questionable. """
        res = dict.fromkeys(ids, '')
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        for product in self.browse(cr, uid, ids, context=context):
            if product.product_variant_ids:
                res[product.id] = "%s/shop/product/%s/" % (base_url, product.product_variant_ids[0].id)
        return res

    _columns = {
        'website_published': fields.boolean('Available in the website'),
        'website_description': fields.html('Description for the website'),
        'suggested_product_id': fields.many2one('product.template', 'Suggested For Product'),
        'suggested_product_ids': fields.one2many('product.template', 'suggested_product_id', 'Suggested Products'),
        'website_size_x': fields.integer('Size X'),
        'website_size_y': fields.integer('Size Y'),
        'website_style_ids': fields.many2many('website.product.style', 'product_website_style_rel', 'product_id', 'style_id', 'Styles'),
        'website_sequence': fields.integer('Sequence', help="Determine the display order in the Website E-commerce"),
        'website_url': fields.function(_website_url, string="Website url", type="char"),
    }
    _defaults = {
        'website_size_x': 1,
        'website_size_y': 1,
        'website_sequence': 1,
        'website_published': False,
    }

    def set_sequence_top(self, cr, uid, ids, context=None):
        cr.execute('SELECT MAX(website_sequence) FROM product_template')
        max_sequence = cr.fetchone()[0] or 0
        return self.write(cr, uid, ids, {'website_sequence': max_sequence + 1}, context=context)

    def set_sequence_bottom(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'website_sequence': 0}, context=context)

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


class product_product(osv.Model):
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
        temp_id = self.browse(cr, uid, ids[0], context=context).product_tmpl_id.id
        return "/website/image?model=product.template&field=%s&id=%s" % (field, temp_id)
