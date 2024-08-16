import base64

from odoo import _, api, exceptions, fields, models


class CardCampaignElement(models.Model):
    _name = 'card.campaign.element'
    _description = 'Marketing Card Campaign Element'

    res_model = fields.Selection(related="campaign_id.res_model", precompute=True, readonly=True, store=True)
    campaign_id = fields.Many2one('card.campaign', required=True, ondelete='cascade')

    card_element_role = fields.Selection([
        ('background', 'Background'),
        ('header', 'Header'),
        ('subheader', 'Sub-Header'),
        ('section_1', 'Section 1'),
        ('subsection_1', 'Sub-Section 1'),
        ('subsection_2', 'Sub-Section 2'),
        ('button', 'Button'),
        ('image_1', 'Image 1'),
        ('image_2', 'Image 2')
    ], required=True)

    card_element_image = fields.Image(attachment=False, compute="_compute_value_fields", readonly=False, store=True)
    card_element_text = fields.Text(compute="_compute_value_fields", readonly=False, store=True)
    # text displayed in list view
    card_element_text_value = fields.Char(string="Text", compute="_compute_card_element_text_value")
    field_path = fields.Char(compute="_compute_value_fields", readonly=False, store=True)
    text_color = fields.Char(compute="_compute_value_fields", readonly=False, store=True)

    render_type = fields.Selection([('image', 'Image'), ('text', 'User Text')], default='text', required=True)
    value_type = fields.Selection([('static', 'Manual'), ('field', 'Dynamic')], default='static', required=True)

    _sql_constraints = [('role_uniq', "unique(campaign_id, card_element_role)", "Each campaign should only have one element for each role.")]

    @api.constrains('field_path', 'res_model')
    def _check_fields(self):
        skip_security = self.env.su or self.env.user._is_admin()
        for element in self.filtered(lambda e: e.value_type == 'field'):
            RenderModel = self.env[element.res_model]
            field_path = element.field_path
            if not field_path:
                raise exceptions.ValidationError(_("field path must be set on %(element_role)s", element_role=element.card_element_role))
            try:
                RenderModel.sudo()._find_value_from_field_path(field_path)
            except (exceptions.UserError, KeyError) as err:
                raise exceptions.ValidationError(
                    _('%(model_name)s.%(field_name)s does not seem reachable.',
                      model_name=RenderModel._name, field_name=field_path)
                ) from err

            if not skip_security and field_path not in RenderModel._marketing_card_allowed_field_paths():
                raise exceptions.ValidationError(
                    _('%(model_name)s.%(field_name)s cannot be used for card campaigns.',
                      model_name=RenderModel._name, field_name=field_path)
                )

            path_start, _dummy, last_field = field_path.rpartition('.')
            # check the last field has a sensible type
            if element.render_type == 'image' and RenderModel.sudo().mapped(path_start)._fields[last_field].type != 'binary':
                raise exceptions.ValidationError(
                    _('%(field_path)s cannot be used as an image value for %(element_role)s',
                      field_path=field_path, element_role=element.card_element_role)
                )

    @api.depends('card_element_text', 'field_path')
    def _compute_card_element_text_value(self):
        for element in self:
            field_val = f'[{element.field_path}]' if element.field_path else ''
            element.card_element_text_value = field_val or element.card_element_text

    @api.depends('render_type', 'value_type')
    def _compute_value_fields(self):
        """Reset values irrelevant to the new type of render or value."""
        for element in self:
            if element.render_type == 'image':
                element.text_color = False

            if element.value_type == 'static':
                element.field_path = False

            if element.value_type == 'field' or element.render_type == 'image':
                element.card_element_text = False

            if element.value_type == 'field' or element.render_type == 'text':
                element.card_element_image = False

    def _get_render_value(self, record):
        """Get the value of the element for a specific record."""
        self.ensure_one()
        if record:
            record.ensure_one()
        if self.value_type == 'field' and record:
            # if the value has changed since this was called, we don't know if sudo is allowed
            if self._origin.field_path != self.field_path:
                self._check_fields()
            # this will be called with sudo from the controller, sudo here too for consistency
            if self.render_type == 'text':
                return record.sudo()._find_value_from_field_path(self.field_path) or ''
            return record.sudo().mapped(self.field_path)[0] or ''
        if self.render_type == 'image':
            return self.card_element_image or ''
        if self.render_type == 'text':
            return self.card_element_text or ''
        return None

    def _get_placeholder_value(self):
        """Placeholder to display in preview mode."""
        self.ensure_one()
        if self.value_type == 'field':
            if self.render_type == 'image':
                return base64.b64encode(self.env['ir.binary']._placeholder())
            if self.render_type == 'text':
                return f'[{self.field_path}]'
        return ''
