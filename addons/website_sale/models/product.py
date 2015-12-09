# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import openerp
from openerp import tools
from openerp.osv import osv, fields
from openerp.tools.translate import html_translate

class product_style(osv.Model):
    _name = "product.style"
    _columns = {
        'name' : fields.char('Style Name', required=True),
        'html_class': fields.char('HTML Classes'),
    }

class product_pricelist(osv.Model):
    _inherit = "product.pricelist"
    _columns = {
        'code': fields.char('E-commerce Promotional Code'),
    }


class product_public_category(osv.osv):
    _name = "product.public.category"
    _inherit = ["website.seo.metadata"]
    _description = "Website Product Category"
    _order = "sequence, name"

    _constraints = [
        (osv.osv._check_recursion, 'Error ! You cannot create recursive categories.', ['parent_id'])
    ]

    def name_get(self, cr, uid, ids, context=None):
        res = []
        for cat in self.browse(cr, uid, ids, context=context):
            names = [cat.name]
            pcat = cat.parent_id
            while pcat:
                names.append(pcat.name)
                pcat = pcat.parent_id
            res.append((cat.id, ' / '.join(reversed(names))))
        return res

    def _name_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
        res = self.name_get(cr, uid, ids, context=context)
        return dict(res)

    _columns = {
        'name': fields.char('Name', required=True, translate=True),
        'complete_name': fields.function(_name_get_fnc, type="char", string='Name'),
        'parent_id': fields.many2one('product.public.category','Parent Category', select=True),
        'child_id': fields.one2many('product.public.category', 'parent_id', string='Children Categories'),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of product categories."),
    }

    # NOTE: there is no 'default image', because by default we don't show
    # thumbnails for categories. However if we have a thumbnail for at least one
    # category, then we display a default image on the other, so that the
    # buttons have consistent styling.
    # In this case, the default image is set by the js code.
    image = openerp.fields.Binary("Image", attachment=True,
        help="This field holds the image used as image for the category, limited to 1024x1024px.")
    image_medium = openerp.fields.Binary("Medium-sized image",
        compute='_compute_images', inverse='_inverse_image_medium', store=True, attachment=True,
        help="Medium-sized image of the category. It is automatically "\
             "resized as a 128x128px image, with aspect ratio preserved. "\
             "Use this field in form views or some kanban views.")
    image_small = openerp.fields.Binary("Small-sized image",
        compute='_compute_images', inverse='_inverse_image_small', store=True, attachment=True,
        help="Small-sized image of the category. It is automatically "\
             "resized as a 64x64px image, with aspect ratio preserved. "\
             "Use this field anywhere a small image is required.")

    @openerp.api.depends('image')
    def _compute_images(self):
        for rec in self:
            rec.image_medium = tools.image_resize_image_medium(rec.image)
            rec.image_small = tools.image_resize_image_small(rec.image)

    def _inverse_image_medium(self):
        for rec in self:
            rec.image = tools.image_resize_image_big(rec.image_medium)

    def _inverse_image_small(self):
        for rec in self:
            rec.image = tools.image_resize_image_big(rec.image_small)

class product_template(osv.Model):
    _inherit = ["product.template", "website.seo.metadata", 'website.published.mixin', 'rating.mixin']
    _order = 'website_published desc, website_sequence desc, name'
    _name = 'product.template'
    _mail_post_access = 'read'

    def _website_url(self, cr, uid, ids, field_name, arg, context=None):
        res = super(product_template, self)._website_url(cr, uid, ids, field_name, arg, context=context)
        for product in self.browse(cr, uid, ids, context=context):
            res[product.id] = "/shop/product/%s" % (product.id,)
        return res

    _columns = {
        # TODO FIXME tde: when website_mail/mail_thread.py inheritance work -> this field won't be necessary
        'website_message_ids': fields.one2many(
            'mail.message', 'res_id',
            domain=lambda self: [
                '&', ('model', '=', self._name), ('message_type', '=', 'comment')
            ],
            string='Website Comments',
        ),
        'website_description': fields.html('Description for the website', sanitize=False, translate=html_translate),
        'alternative_product_ids': fields.many2many('product.template','product_alternative_rel','src_id','dest_id', string='Suggested Products', help='Appear on the product page'),
        'accessory_product_ids': fields.many2many('product.product','product_accessory_rel','src_id','dest_id', string='Accessory Products', help='Appear on the shopping cart'),
        'website_size_x': fields.integer('Size X'),
        'website_size_y': fields.integer('Size Y'),
        'website_style_ids': fields.many2many('product.style', string='Styles'),
        'website_sequence': fields.integer('Sequence', help="Determine the display order in the Website E-commerce"),
        'public_categ_ids': fields.many2many('product.public.category', string='Website Product Category', help="Those categories are used to group similar products for e-commerce."),
    }

    def _defaults_website_sequence(self, cr, uid, *l, **kwargs):
        cr.execute('SELECT MIN(website_sequence)-1 FROM product_template')
        next_sequence = cr.fetchone()[0] or 10
        return next_sequence

    _defaults = {
        'website_size_x': 1,
        'website_size_y': 1,
        'website_sequence': _defaults_website_sequence,
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


class product_product(osv.Model):
    _inherit = "product.product"

    # Wrappers for call_kw with inherits
    def open_website_url(self, cr, uid, ids, context=None):
        template_id = self.browse(cr, uid, ids, context=context).product_tmpl_id.id
        return self.pool['product.template'].open_website_url(cr, uid, [template_id], context=context)

    def website_publish_button(self, cr, uid, ids, context=None):
        template_id = self.browse(cr, uid, ids, context=context).product_tmpl_id.id
        return self.pool['product.template'].website_publish_button(cr, uid, [template_id], context=context)

    def website_publish_button(self, cr, uid, ids, context=None):
        template_id = self.browse(cr, uid, ids, context=context).product_tmpl_id.id
        return self.pool['product.template'].website_publish_button(cr, uid, [template_id], context=context)

class product_attribute(osv.Model):
    _inherit = "product.attribute"
    _columns = {
        'type': fields.selection([('radio', 'Radio'), ('select', 'Select'), ('color', 'Color'), ('hidden', 'Hidden')], string="Type"),
    }
    _defaults = {
        'type': lambda *a: 'radio',
    }


class product_attribute_value(osv.Model):
    _inherit = "product.attribute.value"
    _columns = {
        'color': fields.char("HTML Color Index", help="Here you can set a specific HTML color index (e.g. #ff0000) to display the color on the website if the attibute type is 'Color'."),
    }

    # TODO in master: remove this function and change 'color' field name
    def write(self, cr, uid, ids, vals, context=None):
        # ignore write coming from many2many_tags color system
        if vals.keys() == ['color'] and isinstance(vals['color'], (int, long)):
            vals = {}
        return super(product_attribute_value, self).write(cr, uid, ids, vals, context=context)
