# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from io import BytesIO
import base64
import requests
import os
from PIL import ImageDraw, ImageFont, Image

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import file_path
from odoo.modules.module import get_module_path

def _get_font_name_to_path_map():
    walk = os.walk(get_module_path('web'))
    return {file: f'{path}/{file}' for path, _, files in walk for file in files if file.endswith('.ttf')}

class PostTemplateElement(models.Model):
    _name = 'social.share.post.template.element'
    _order = 'sequence, id DESC'
    _description = 'Social Share Template Layer'

    @staticmethod
    def _get_font_name_to_path_map():
        return _get_font_name_to_path_map()

    @staticmethod
    def _get_available_fonts():
        return [(file, file) for file in _get_font_name_to_path_map()]

    @staticmethod
    def _get_text_types():
        return [('field_txt', 'Field Text'), ('txt', 'Static Text')]

    name = fields.Char()
    type = fields.Selection(_get_text_types() + [('img', 'Static Image'), ('color', 'Color')], default='img', required=True)

    role = fields.Selection([
        ('background', 'Background'),
        ('header', 'Header'),
        ('subheader', 'Sub-Header'),
        ('section-1', 'Section 1'),
        ('subsection-1', 'Sub-Section 1'),
        ('subsection-2', 'Sub-Section 2'),
        ('button', 'Button'),
        ('image-1', 'Image 1'),
        ('image-2', 'Image 2')
    ])

    # Can be any of:
    # - static text
    # - path to a field for the model
    # - color value as hex rgb
    text_val = fields.Text()

    text_align = fields.Selection([('left', 'Left'), ('center', 'Center')])
    text_align_vert = fields.Selection([('top', 'Top'), ('center', 'Center')])
    text_font_size = fields.Integer()
    text_font = fields.Selection(selection=_get_available_fonts())
    text_color = fields.Char()

    image_crop = fields.Selection([('rect', 'Rectangle'), ('roundrect', 'Rounded Rectangle'), ('circ', 'Circle')])
    image = fields.Image()

    model_id = fields.Many2one('ir.model', related="template_id.model_id")
    model = fields.Char(related='model_id.model', string="Model Name")

    x_pos = fields.Integer(default=0, required=True)
    y_pos = fields.Integer(default=0, required=True)
    x_size = fields.Integer(default=0, required=True)
    y_size = fields.Integer(default=0, required=True)

    sequence = fields.Integer(default=1, required=True)
    template_id = fields.Many2one('social.share.post.template')

    @staticmethod
    def _get_raw_font(path):
        try:
            return file_path(path)
        except IOError:
            return None

    def _get_position(self):
        return (self.x_pos, self.y_pos)
    def _get_size(self):
        return (self.x_size, self.y_size)
    def _get_bounds(self):
        return ((self.x_pos, self.y_pos), (self.x_pos + self.x_size, self.y_pos + self.y_size))

    def _get_font(self, font_map=None):
        self.ensure_one()
        font = None
        if self.text_font and font_map and font_map.get(self.text_font):
            font = self._get_raw_font(font_map[self.text_font])
        if font:
            return ImageFont.truetype(font, self.text_font_size)
        return ImageFont.load_default()

    @staticmethod
    def _get_color(color_string):
        if not isinstance(color_string, str) or len(color_string) != 6:
            raise UserError(_('Invalid color string: "%s"', color_string))
        r, g, b = (int(color_string[start:start + 2], 16) for start in range(0, 6, 2))
        return (r, g, b)

    def get_image(self):
        if self.image:
            return self.image
        #elif self.image_url:
        #    try:
        #        response = requests.request('get', self.image_url, timeout=5)
        #        return base64.b64encode(response.content)
        #    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.HTTPError):
        #        return None
        return None

    def get_text(self, record=None):
        if self.type == 'txt':
            return self.text_val
        elif self.type == 'field_txt':
            field = self.text_val
            if record:
                return record[field]
            # get translated field name
            field_name = self.env['ir.model.fields'].sudo().search([
                ('model_id', '=', self.model_id.id), ('name', '=', field)
            ], limit=1).name
            return f'[{field_name}]'
        elif self.type == 'usr_txt':
            return _('User Text')
        return None
