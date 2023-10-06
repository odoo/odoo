
from odoo import _, api, exceptions, fields, models
from .render.renderer_text import FieldTextRenderer, UserTextRenderer
from .render.renderer_image import ImageFieldShapeRenderer, ImageStaticShapeRenderer

render_class_from_type = {
    'image': {
        'static': ImageStaticShapeRenderer,
        'field': ImageFieldShapeRenderer,
    },
    'text': {
        'static': UserTextRenderer,
        'field': FieldTextRenderer
    },
}

reset_dict_from_type = {
    'image': {
        'static': {field: False for field in ('field_path', 'text', 'text_color')},
        'field': {field: False for field in ('image', 'text', 'text_color')},
    },
    'text': {
        'static': {field: False for field in ('field_path', 'image', 'shape')},
        'field': {field: False for field in ('text', 'image', 'shape')}
    },
}

class ImageRenderElement(models.AbstractModel):
    _name = 'social.share.image.render.element'
    _description = 'Social Share Render Element'
    _rec_name = 'role'

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

    model = fields.Char()
    render_type = fields.Selection([('image', 'Image'), ('text', 'User Text')], default='text', required=True, ondelete={'image': 'cascade', 'text': 'cascade'})
    value_type = fields.Selection([('static', 'Manual'), ('field', 'Dynamic')], default='static', required=True)

    # shapes generic
    shape = fields.Selection([('rect', 'Rectangle'), ('roundrect', 'Rounded Rectangle'), ('circ', 'Circle')], default='rect')
    # image shape
    image = fields.Image(attachment=False)
    # text user input
    text = fields.Text()
    text_color = fields.Char()
    # text field
    field_path = fields.Char()

    @api.constrains('model', 'field_path')
    def _check_field_allowed(self):
        for element in self.filtered('field_path'):
            if not element.model or element.model not in self.env:
                raise exceptions.ValidationError(_('You must select a valid model to use field values.'))
            # allow system to set any field
            if not (self.env.su or self.env.user.has_group('base.group_system')):
                allow_rules = self.env['social.share.field.allow'].search([]).grouped('model_id.model')
                Model = self.env[element.model].sudo()
                for field in element.field_path.split('.'):
                    if all(rule.field_id.name != field for rule in allow_rules.get(Model._name, [])):
                        raise exceptions.ValidationError(_('Field %(field_name)s of %(model_name)s is not allowed in social campaigns', field_name=field, model_name=value._name))
                    Model = Model[field]
                final_value = Model
                if not isinstance(final_value, models.Model):
                    raise exceptions.ValidationError(_("Field path %(field_path)s should point to a value, not a model.", field_path=element.field_path))

    @api.constrains('render_type', 'value_type')
    def _check_type_combination(self):
        for element in self:
            if not element._get_renderer_class():
                raise exceptions.ValidationError(_('%(dynamic_type)s %(output_type)s cannot be rendered', dynamic_type=self.value_type, output_type=self.render_type))

    def _clear_values(self):
        self.write({
            'image': False,
            'text': False,
            'field_path': False
        })

    @api.onchange('render_type', 'value_type')
    def _onchange_type(self):
        for element in self:
            if reset_dict_from_type.get(element.render_type, {}).get(element.value_type):
                element.write(reset_dict_from_type[element.render_type][element.value_type])

    def _get_renderer_class(self):
        return render_class_from_type.get(self.render_type, {}).get(self.value_type)

    def _get_renderer_constructor_values(self):
        return dict()

    def action_edit_from_campaign(self):
        action = self.env['ir.action.act_window']._from_xml_id('social_share.action_social_share_campaign_template_element')
        return action | {'context': {'dialog_size': 'small', 'active_id': self.id}}
