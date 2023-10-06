# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ..utils.image_render_utils import align_text, get_shape, fit_to_mask, text_fits_height
from io import BytesIO
import base64
from PIL import ImageDraw, Image

from odoo import _, api, Command, fields, models
from odoo.exceptions import UserError


TEMPLATE_DIMENSIONS = (1200, 630)
TEMPLATE_RATIO = 40 / 21
FONTS = ['NotoSans-VF.ttf', 'NotoSans[wght].ttf', 'Cantarell-VF.otf']

class PostTemplate(models.Model):
    _name = 'social.share.post.template'
    _description = 'Social Share Template'

    name = fields.Char(compute='_compute_name', store=True, required=True)
    image = fields.Image(compute='_compute_image')
    model_id = fields.Many2one(
        'ir.model', domain=lambda self: [('model', 'in', self._get_valid_target_models())],
        related='post_id.model_id', store=True
    )

    # if empty, is a generic copyable template
    post_id = fields.One2many('social.share.post', inverse_name='share_template_id')
    # similar templates where preserving elements with 'roles' makes sense
    variant_ids = fields.One2many('social.share.post.template', inverse_name='parent_variant_id')
    parent_variant_id = fields.Many2one('social.share.post.template', copy=False)

    background = fields.Image(compute='_compute_background', inverse='_inverse_background')

    layers = fields.One2many('social.share.post.template.element', inverse_name='template_id', copy=True)

    def _get_valid_target_models(self):
        return self.env['social.share.field.allow'].search([]).sudo().field_id.model_id.mapped('model')

    @api.depends('post_id.name')
    def _compute_name(self):
        for template in self:
            if template.post_id:
                template.name = _('%(post_name)s (campaign template)', post_name=template.post_id.name)

    def _compute_background(self):
        for template in self:
            template.background = template.layers[0].get_image() if template.layers else None

    def _inverse_background(self):
        for template in self:
            template.layers += self.env['social.share.post.template.element'].create({
                'image': template.background,
                'name': 'background',
                'role': 'background',
                'x_size': TEMPLATE_DIMENSIONS[0],
                'y_size': TEMPLATE_DIMENSIONS[1],
                'sequence': 0,
            })

    def copy_data(self, default=None):
        default = dict(default or {})
        default.setdefault('name', _("%s (copy)", self.name))
        return super().copy_data(default)

    def _update_from_variant(self, template_id):
        retained_layers = self.env['social.share.post.template.element']
        if self._compatible_layers_with(template_id):
            retained_layers = self.layers.filtered('role')
        unlink_commands = [Command.unlink(layer.id) for layer in self.layers - retained_layers]
        replacing_layers = template_id.layers.filtered(lambda layer: not layer.role or layer.role not in retained_layers.mapped('role'))
        replacing_create_values = [layer.copy_data({'template_id': False})[0] for layer in replacing_layers]
        self.write({'layers': unlink_commands + [Command.create(vals) for vals in replacing_create_values]})

    def _compatible_layers_with(self, template_id):
        self.ensure_one()
        template_id.ensure_one()
        return set(self.layers.mapped('role')) == set(template_id.layers.mapped('role'))

    @api.depends(lambda self: [f'layers.{field}' for field in self.env['social.share.post.template.element']._fields] + ['layers'])
    def _compute_image(self):
        self.image = self._generate_image_b64()

    def _generate_image_b64(self, record=None):
        return base64.encodebytes(self._generate_image_bytes(record=record))

    def _generate_image_bytes(self, record=None):
        final_image = Image.new('RGBA', TEMPLATE_DIMENSIONS, color=(0, 0, 0))
        fonts = self.env['social.share.post.template.element']._get_font_name_to_path_map()
        for layer in self.layers:
            image_b64 = layer.get_image()
            text = layer.get_text(record)
            if layer.type == 'color':
                shape = get_shape(layer.image_crop or 'rect', layer._get_color(layer.text_val), 4, layer._get_size())
                final_image.paste(shape, layer._get_position(), shape)
            elif image_b64:
                image = Image.open(BytesIO(base64.b64decode(image_b64))).convert('RGBA')
                image = fit_to_mask(image, layer.image_crop, xy=layer._get_size())
                if any(layer._get_size()) and image.size != layer._get_size():
                    image = image.crop((0, 0, *layer._get_size()))
                final_image.paste(image, layer._get_position(), image)
            elif text:
                font = layer._get_font(fonts)
                editor = ImageDraw.ImageDraw(final_image)
                text_lines = align_text(text, font, (layer._get_position(), layer._get_size()), editor, layer.text_align or 'left')
                # if biggest y and smallest Ys don't fit in the size
                if layer.y_size and (text_lines[-1][0][1][1] > layer.y_pos + layer.y_size or text_lines[0][0][0][1] < layer.y_pos):
                    raise ValueError(_('The text "%(text)s" cannot fit in the requested height %(height)d', text=text, height=layer.y_size))
                for (pos, dummy), line in text_lines:
                    editor.text(
                        pos, line, font=font,
                        fill=layer._get_color(layer.text_color if layer.text_color else 'ffffff'))
        final_image_bytes = BytesIO()
        final_image.convert('RGB').save(final_image_bytes, "PNG")
        return final_image_bytes.getvalue()
