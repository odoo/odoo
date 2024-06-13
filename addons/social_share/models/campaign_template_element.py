# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, exceptions, fields, models
from .render.renderer_text import FieldTextRenderer, UserTextRenderer
from .render.renderer_image import ColorShapeRenderer, ImageFieldShapeRenderer, ImageStaticShapeRenderer


template_text_option_fields = (
    'text_align',
    'text_align_vert',
    'text_font_size',
    'text_font_ids',
    'text_color',
)

render_class_from_type = {
    'shape': {
        'static': ColorShapeRenderer,
    },
}

reset_dict_from_type = {
    'image': {
        'static': {field: False for field in template_text_option_fields},
        'field': {field: False for field in template_text_option_fields},
    },
    'text': {
        'static': {field: False for field in ('color')},
        'field': {field: False for field in ('color')}
    },
    'shape': {
        'static': {field: False for field in ('field_path', 'text', 'image', *template_text_option_fields)},
    },
}

class TemplateRenderElement(models.Model):
    _name = 'social.share.template.render.element'
    _inherit = 'social.share.image.render.element'
    _description = 'Social Share Template Layer'
    _order = 'sequence, id DESC'
    _sql_constraints = [('role_uniq', "unique(template_id, role)", "Each template should only have one element for each role.")]

    template_id = fields.Many2one('social.share.campaign.template', ondelete='cascade')
    model = fields.Char(related='template_id.model_id.model')

    x_pos = fields.Integer(default=0, required=True)
    y_pos = fields.Integer(default=0, required=True)
    x_size = fields.Integer(default=0, required=True)
    y_size = fields.Integer(default=0, required=True)

    sequence = fields.Integer(default=1, required=True)

    render_type = fields.Selection(selection_add=[('shape', 'Shape')], required=True, ondelete={'shape': 'cascade'})

    # color shape
    color = fields.Char()

    # text generic
    text_align = fields.Selection([('left', 'Left'), ('center', 'Center')])
    text_align_vert = fields.Selection([('top', 'Top'), ('center', 'Center')])
    text_font_size = fields.Integer()
    text_font_ids = fields.Many2many('social.share.text.font')

    # if any required element has no value to render, this element won't be rendered
    required_element_ids = fields.Many2many('social.share.template.render.element', relation="social_share_element_requirements", column1='social_share_element_required', column2='social_share_sub_element', copy=False)
    sub_element_ids = fields.Many2many('social.share.template.render.element', relation="social_share_element_requirements", column1='social_share_sub_element', column2='social_share_element_required', copy=False)

    def _onchange_type(self):
        super()._onchange_type()
        for element in self:
            if reset_dict_from_type.get(element.render_type, {}).get(element.value_type):
                element.write(reset_dict_from_type[element.render_type][element.value_type])

    def _get_renderer(self):
        renderer_class = self._get_renderer_class()
        renderer_values = self._get_renderer_constructor_values(renderer_class)
        return renderer_class(**renderer_values)

    def _get_renderer_constructor_values(self, renderer_class):
        """Return a dict containing kwargs to construct a renderer object."""
        common_dict = {
            'pos': (self.x_pos, self.y_pos),
            'size': (self.x_size, self.y_size),
        }
        if renderer_class == ImageStaticShapeRenderer:
            return common_dict | {
                'shape': self.shape,
                'image': self.image,
            }
        if renderer_class == ImageFieldShapeRenderer:
            return common_dict | {
                'shape': self.shape,
                'field_path': self.field_path,
                'use_placeholder': self.role != 'background',
            }
        if renderer_class == ColorShapeRenderer:
            return common_dict | {
                'shape': self.shape,
                'color': self.color,
            }
        # TODO probably needs to be batch-able now...
        text_fonts = self.text_font_ids or self.env['social.share.text.font'].search([('is_fallback', '=', True)])
        text_common_dict = {
            'text_align_horizontal': self.text_align,
            'text_align_vertical': self.text_align_vert,
            'text_color': self.text_color,
            'text_fonts': text_fonts,
            'text_font_size': self.text_font_size,
        }
        if renderer_class == UserTextRenderer:
            return common_dict | text_common_dict | {
                'text': self.text,
            }
        if renderer_class == FieldTextRenderer:
            return common_dict | text_common_dict | {
                'field_path': self.field_path,
                'model': self.model,
            }
        return super()._get_renderer_constructor_values()

    def _get_renderer_class(self):
        return render_class_from_type.get(self.render_type, {}).get(self.value_type) or super()._get_renderer_class()

    # used for data generation
    def _set_depends_on_roles(self, roles):
        """Looks for a layer with the specified role in the template and set a dependency on it."""
        dependency = self.template_id.layers.filtered(lambda layer: layer.role in roles)
        if len(dependency) != len(roles):
            raise exceptions.UserError(_("Could not find all layers with these roles %(roles)s", roles=roles))
        self.required_element_ids += dependency

    @api.returns('self', lambda value: value.id)
    def _copy_with_dependencies(self, defaults, roles):
        """Copy but add dependencies on roles."""
        copy = self.copy(default=defaults)
        copy._set_depends_on_roles(roles)
        return copy
