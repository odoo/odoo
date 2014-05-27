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

class product_attribue(osv.Model):
    # TODO merge product.attribute, mrp.properties product_manufacturer_attributes
    _name = "product.attribute"
    _columns = {
        'name': fields.char('Name', translate=True, required=True),
        'value_ids': fields.one2many('product.attribute.value', 'attribute_id', 'Values'),
    }

class product_attribute_value(osv.Model):
    _name = "product.attribute.value"
    _columns = {
        'attribute_id': fields.many2one('product.attribute', 'attribute', required=True),
        'name': fields.char('Value', translate=True, required=True),
    }

class product_attribute_line(osv.Model):
    _name = "product.attribute.line"
    _order = 'attribute_id, value_id'
    _columns = {
        'product_tmpl_id': fields.many2one('product.template', 'Product', required=True),
        'attribute_id': fields.many2one('product.attribute', 'attribute', required=True),
        'value_id': fields.many2one('product.attribute.value', 'Textual Value'),
    }

    def onchange_attribute_id(self, cr, uid, ids, attribute_id, context=None):
        return {'value': {'value_id': False}}

class product_style(osv.Model):
    _name = "product.style"
    _columns = {
        'name' : fields.char('Style Name', required=True),
        'html_class': fields.char('HTML Classes'),
    }

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
        for product in self.browse(cr, uid, ids, context=context):
            res[product.id] = "/shop/product/%s" % (product.id,)
        return res

    _columns = {
        'attribute_lines': fields.one2many('product.attribute.line', 'product_tmpl_id', 'Product attributes'),
        # TODO FIXME tde: when website_mail/mail_thread.py inheritance work -> this field won't be necessary
        'website_message_ids': fields.one2many(
            'mail.message', 'res_id',
            domain=lambda self: [
                '&', ('model', '=', self._name), ('type', '=', 'comment')
            ],
            string='Website Comments',
        ),
        'website_published': fields.boolean('Available in the website'),
        'website_description': fields.html('Description for the website'),
        'alternative_product_ids': fields.many2many('product.template','product_alternative_rel','src_id','dest_id', string='Alternative Products', help='Appear on the product page'),
        'accessory_product_ids': fields.many2many('product.template','product_accessory_rel','src_id','dest_id', string='Accessory Products', help='Appear on the shopping cart'),
        'website_size_x': fields.integer('Size X'),
        'website_size_y': fields.integer('Size Y'),
        'website_style_ids': fields.many2many('product.style', string='Styles'),
        'website_sequence': fields.integer('Sequence', help="Determine the display order in the Website E-commerce"),
        'website_url': fields.function(_website_url, string="Website url", type="char"),
    }

    def _defaults_website_sequence(self, cr, uid, *l, **kwargs):
        cr.execute('SELECT MAX(website_sequence)+1 FROM product_template')
        next_sequence = cr.fetchone()[0] or 0
        return next_sequence

    _defaults = {
        'website_size_x': 1,
        'website_size_y': 1,
        'website_sequence': _defaults_website_sequence,
        'website_published': False,
    }

    def website_reorder(self, cr, uid, ids, operation=None, context=None):
        if operation == "top":
            cr.execute('SELECT MAX(website_sequence) FROM product_template')
            seq = (cr.fetchone()[0] or 0) + 1
        if operation == "bottom":
            cr.execute('SELECT MIN(website_sequence) FROM product_template')
            seq = (cr.fetchone()[0] or 0) -1
        if operation == "up":
            product = self.browse(cr, uid, ids[0], context=context)
            cr.execute("""  SELECT id, website_sequence FROM product_template
                            WHERE website_sequence > %s AND website_published = %s ORDER BY website_sequence ASC LIMIT 1""" % (product.website_sequence, product.website_published))
            prev = cr.fetchone()
            if prev:
                self.write(cr, uid, [prev[0]], {'website_sequence': product.website_sequence}, context=context)
                return self.write(cr, uid, [ids[0]], {'website_sequence': prev[1]}, context=context)
            else:
                return self.website_reorder(cr, uid, ids, operation='top', context=context)
        if operation == "down":
            product = self.browse(cr, uid, ids[0], context=context)
            cr.execute("""  SELECT id, website_sequence FROM product_template
                            WHERE website_sequence < %s AND website_published = %s ORDER BY website_sequence DESC LIMIT 1""" % (product.website_sequence, product.website_published))
            next = cr.fetchone()
            if next:
                self.write(cr, uid, [next[0]], {'website_sequence': product.website_sequence}, context=context)
                return self.write(cr, uid, [ids[0]], {'website_sequence': next[1]}, context=context)
            else:
                return self.website_reorder(cr, uid, ids, operation='bottom', context=context)
        return self.write(cr, uid, ids, {'website_sequence': seq}, context=context)

    def img(self, cr, uid, ids, field='image_small', context=None):
        return "/website/image?model=%s&field=%s&id=%s" % (self._name, field, ids[0])

class product_product(osv.Model):
    _inherit = "product.product"

    def _website_url(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for product in self.browse(cr, uid, ids, context=context):
            res[product.id] = "/shop/product/%s" % (product.product_tmpl_id.id,)
        return res

    _columns = {
        'website_url': fields.function(_website_url, string="Website url", type="char"),
    }

    def img(self, cr, uid, ids, field='image_small', context=None):
        temp_id = self.browse(cr, uid, ids[0], context=context).product_tmpl_id.id
        return "/website/image?model=product.template&field=%s&id=%s" % (field, temp_id)

# vim:et:
