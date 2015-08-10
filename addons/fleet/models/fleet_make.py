# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from openerp import api, fields, models, tools


class FleetMake(models.Model):
    _name = 'fleet.make'
    _description = 'Make of the vehicle'
    _order = 'name asc, id asc'

    name = fields.Char(string='Make', required=True)
    image = fields.Binary(string="Logo", help="This field holds the image used as logo for the brand,limited to 1024x1024px.")
    image_medium = fields.Binary(compute='_compute_get_image', inverse='_compute_set_image', string="Medium-sized photo", store=True,
                                 help="Medium-sized logo of the brand. It is automatically "
                                      "resize as a 128x128px image, with aspect ratio preserved. "
                                      "Use this field in form views or some kanban views.")
    image_small = fields.Binary(compute='_compute_get_image', inverse='_compute_set_image', string="Small-sized photo", store=True,
                                help="Small-sized photo of the brand. It is automatically "
                                     "resize as a 64x64px image, with aspect ratio preserved. "
                                     "Use this field anywhere a small image is required.")

    @api.one
    @api.depends('image')
    def _compute_get_image(self):
        make_images = tools.image_get_resized_images(self.image)
        self.image_medium = make_images.get('image_medium')
        self.image_small = make_images.get('image_small')

    @api.one
    def _compute_set_image(self):
        self.image = tools.image_resize_image_big(self.image_medium)
