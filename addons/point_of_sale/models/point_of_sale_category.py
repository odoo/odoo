# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import api, fields, models, tools, _


class PosCategory(models.Model):
    _name = "pos.category"
    _description = "Public Category"
    _order = "sequence, name"

    _constraints = [
        (models.Model._check_recursion, _('Error ! You cannot create recursive categories.'), ['parent_id'])
    ]

    @api.multi
    def name_get(self):
        res = []
        for cat in self:
            names = [cat.name]
            pcat = cat.parent_id
            while pcat:
                names.append(pcat.name)
                pcat = pcat.parent_id
            res.append((cat.id, ' / '.join(reversed(names))))
        return res

    @api.depends('image')
    def _get_image(self):
        for cat in self:
            cat.image_medium = tools.image_get_resized_images(cat.image)

    @api.one
    def _set_image(self):
        return self.write({'image': tools.image_resize_image_big(self.image)})

    name = fields.Char(required=True, translate=True)
    parent_id = fields.Many2one('pos.category', string='Parent Category', index=True)
    child_id = fields.One2many('pos.category', 'parent_id', string='Children Categories')
    sequence = fields.Integer(help="Gives the sequence order when displaying a list of product categories.")
    # NOTE: there is no 'default image', because by default we don't show thumbnails for categories. However if we have a thumbnail
    # for at least one category, then we display a default image on the other, so that the buttons have consistent styling.
    # In this case, the default image is set by the js code.
    # NOTE2: image: all image fields are base64 encoded and PIL-supported
    image = fields.Binary(
        help="This field holds the image used as image for the cateogry, limited to 1024x1024px.")
    image_medium = fields.Binary(
        compute='_get_image', inverse='_set_image',
        string="Medium-sized image", store=True,
        help="Medium-sized image of the category. It is automatically "\
             "resized as a 128x128px image, with aspect ratio preserved. "\
             "Use this field in form views or some kanban views.")
    image_small = fields.Binary(
        compute='_get_image', inverse='_set_image',
        string="Smal-sized image",
        help="Small-sized image of the category. It is automatically "\
             "resized as a 64x64px image, with aspect ratio preserved. "\
             "Use this field anywhere a small image is required.")
