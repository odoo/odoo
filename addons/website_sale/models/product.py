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
        'code': fields.char('Promotional Code'),
    }


class product_template(osv.Model):
    _inherit = ["product.template", "website.seo.metadata"]
    _order = 'website_published desc, website_sequence desc, name'
    _name = 'product.template'
    _mail_post_access = 'read'

    def _website_url(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, '')
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        for product in self.browse(cr, uid, ids, context=context):
            res[product.id] = "%s/shop/product/%s/" % (base_url, product.id)
        return res

    _columns = {
        'website_published': fields.boolean('Available in the website'),
        'website_description': fields.html('Description for the website'),
        # TDE TODO FIXME: when website_mail/mail_thread.py inheritance work -> this field won't be necessary
        'website_message_ids': fields.one2many(
            'mail.message', 'res_id',
            domain=lambda self: [
                '&', ('model', '=', self._name), ('type', '=', 'comment')
            ],
            string='Website Messages',
            help="Website communication history",
        ),
        'alternative_product_ids': fields.many2many('product.template','product_alternative_rel','src_id','dest_id', string='Alternative Products', help='Appear on the product page'),
        'accessory_product_ids': fields.many2many('product.template','product_accessory_rel','src_id','dest_id', string='Accessory Products', help='Appear on the shopping cart'),
        'website_size_x': fields.integer('Size X'),
        'website_size_y': fields.integer('Size Y'),
        'website_style_ids': fields.many2many('product.style', 'product_website_style_rel', 'product_id', 'style_id', 'Styles'),
        'website_sequence': fields.integer('Sequence', help="Determine the display order in the Website E-commerce"),
        'website_url': fields.function(_website_url, string="Website url", type="char"),
    }

    def __defaults_website_sequence(self, cr, uid, *kwargs):
        cr.execute('SELECT MAX(website_sequence) FROM product_template')
        max_sequence = cr.fetchone()[0] or 0
        return max_sequence + 1

    _defaults = {
        'website_size_x': 1,
        'website_size_y': 1,
        'website_sequence': __defaults_website_sequence,
        'website_published': False,
    }

    def set_sequence_top(self, cr, uid, ids, context=None):
        cr.execute('SELECT MAX(website_sequence) FROM product_template')
        max_sequence = cr.fetchone()[0] or 0
        return self.write(cr, uid, ids, {'website_sequence': max_sequence + 1}, context=context)

    def set_sequence_bottom(self, cr, uid, ids, context=None):
        cr.execute('SELECT MIN(website_sequence) FROM product_template')
        min_sequence = cr.fetchone()[0] or 0
        return self.write(cr, uid, ids, {'website_sequence': min_sequence -1}, context=context)

    def set_sequence_up(self, cr, uid, ids, context=None):
        product = self.browse(cr, uid, ids[0], context=context)
        cr.execute("""  SELECT id, website_sequence FROM product_template
                        WHERE website_sequence > %s AND website_published = %s ORDER BY website_sequence ASC LIMIT 1""" % (product.website_sequence, product.website_published))
        prev = cr.fetchone()
        if prev:
            self.write(cr, uid, [prev[0]], {'website_sequence': product.website_sequence}, context=context)
            return self.write(cr, uid, [ids[0]], {'website_sequence': prev[1]}, context=context)
        else:
            return self.set_sequence_top(cr, uid, ids, context=context)

    def set_sequence_down(self, cr, uid, ids, context=None):
        product = self.browse(cr, uid, ids[0], context=context)
        cr.execute("""  SELECT id, website_sequence FROM product_template
                        WHERE website_sequence < %s AND website_published = %s ORDER BY website_sequence DESC LIMIT 1""" % (product.website_sequence, product.website_published))
        next = cr.fetchone()
        if next:
            self.write(cr, uid, [next[0]], {'website_sequence': product.website_sequence}, context=context)
            return self.write(cr, uid, [ids[0]], {'website_sequence': next[1]}, context=context)
        else:
            return self.set_sequence_bottom(cr, uid, ids, context=context)

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
        for product in self.browse(cr, uid, ids, context=context):
            res[product.id] = "%s/shop/product/%s/" % (base_url, product.product_tmpl_id.id)
        return res

    _columns = {
        'website_url': fields.function(_website_url, string="Website url", type="char"),
    }

    def img(self, cr, uid, ids, field='image_small', context=None):
        temp_id = self.browse(cr, uid, ids[0], context=context).product_tmpl_id.id
        return "/website/image?model=product.template&field=%s&id=%s" % (field, temp_id)
