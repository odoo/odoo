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

from openerp import tools
from openerp.osv import osv, fields

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


class product_public_category(osv.osv):
    _name = "product.public.category"
    _description = "Public Category"
    _order = "sequence, name"

    _constraints = [
        (osv.osv._check_recursion, 'Error ! You cannot create recursive categories.', ['parent_id'])
    ]

    def name_get(self, cr, uid, ids, context=None):
        if not len(ids):
            return []
        reads = self.read(cr, uid, ids, ['name','parent_id'], context=context)
        res = []
        for record in reads:
            name = record['name']
            if record['parent_id']:
                name = record['parent_id'][1]+' / '+name
            res.append((record['id'], name))
        return res

    def _name_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
        res = self.name_get(cr, uid, ids, context=context)
        return dict(res)

    def _get_image(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = tools.image_get_resized_images(obj.image)
        return result

    def _set_image(self, cr, uid, id, name, value, args, context=None):
        return self.write(cr, uid, [id], {'image': tools.image_resize_image_big(value)}, context=context)

    _columns = {
        'name': fields.char('Name', required=True, translate=True),
        'complete_name': fields.function(_name_get_fnc, type="char", string='Name'),
        'parent_id': fields.many2one('product.public.category','Parent Category', select=True),
        'child_id': fields.one2many('product.public.category', 'parent_id', string='Children Categories'),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of product categories."),

        # NOTE: there is no 'default image', because by default we don't show thumbnails for categories. However if we have a thumbnail
        # for at least one category, then we display a default image on the other, so that the buttons have consistent styling.
        # In this case, the default image is set by the js code.
        # NOTE2: image: all image fields are base64 encoded and PIL-supported
        'image': fields.binary("Image",
            help="This field holds the image used as image for the cateogry, limited to 1024x1024px."),
        'image_medium': fields.function(_get_image, fnct_inv=_set_image,
            string="Medium-sized image", type="binary", multi="_get_image",
            store={
                'product.public.category': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Medium-sized image of the category. It is automatically "\
                 "resized as a 128x128px image, with aspect ratio preserved. "\
                 "Use this field in form views or some kanban views."),
        'image_small': fields.function(_get_image, fnct_inv=_set_image,
            string="Smal-sized image", type="binary", multi="_get_image",
            store={
                'product.public.category': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Small-sized image of the category. It is automatically "\
                 "resized as a 64x64px image, with aspect ratio preserved. "\
                 "Use this field anywhere a small image is required."),
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
        'accessory_product_ids': fields.many2many('product.product','product_accessory_rel','src_id','dest_id', string='Accessory Products', help='Appear on the shopping cart'),
        'website_size_x': fields.integer('Size X'),
        'website_size_y': fields.integer('Size Y'),
        'website_style_ids': fields.many2many('product.style', string='Styles'),
        'website_sequence': fields.integer('Sequence', help="Determine the display order in the Website E-commerce"),
        'website_url': fields.function(_website_url, string="Website url", type="char"),
        'public_categ_ids': fields.many2many('product.public.category', string='Public Category', help="Those categories are used to group similar products for e-commerce."),
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

class product_attribute(osv.Model):
    _inherit = "product.attribute"
    _columns = {
        'type': fields.selection([('radio', 'Radio'), ('select', 'Select'), ('color', 'Color'), ('hidden', 'Hidden')], string="Type", type="char"),
    }
    _defaults = {
        'type': lambda *a: 'radio',
    }

class product_attribute_value(osv.Model):
    _inherit = "product.attribute.value"
    _columns = {
        'color': fields.char("HTML Color Index", help="Here you can set a specific HTML color index (e.g. #ff0000) to display the color on the website if the attibute type is 'Color'."),
    }
