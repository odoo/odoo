# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import tools
from openerp.osv import fields, osv


class pos_category(osv.osv):
    _name = "pos.category"
    _description = "Public Category"
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
        'parent_id': fields.many2one('pos.category','Parent Category', select=True),
        'child_id': fields.one2many('pos.category', 'parent_id', string='Children Categories'),
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
                'pos.category': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Medium-sized image of the category. It is automatically "\
                 "resized as a 128x128px image, with aspect ratio preserved. "\
                 "Use this field in form views or some kanban views."),
        'image_small': fields.function(_get_image, fnct_inv=_set_image,
            string="Smal-sized image", type="binary", multi="_get_image",
            store={
                'pos.category': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Small-sized image of the category. It is automatically "\
                 "resized as a 64x64px image, with aspect ratio preserved. "\
                 "Use this field anywhere a small image is required."),
    }