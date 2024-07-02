import base64

from odoo import _, api, exceptions, fields, models

class CardCampaignElement(models.Model):
    _name = 'card.campaign.element'
    _description = 'Marketing Card Campaign Element'

    res_model = fields.Selection(related='campaign_id.res_model')
    campaign_id = fields.Many2one('card.campaign', required=True, ondelete='cascade')

    role = fields.Selection([
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

    render_type = fields.Selection([('image', 'Image'), ('text', 'User Text')], default='text', required=True)
    value_type = fields.Selection(
        [('static', 'Manual'), ('field', 'Dynamic')], compute="_compute_value_type",
        readonly=False, required=True, store=True
    )

    # image shape
    image = fields.Image(attachment=False, compute="_compute_image", readonly=False, store=True)
    # text user input
    text = fields.Text(compute="_compute_text", readonly=False, store=True)
    text_color = fields.Char(compute="_compute_text_color", readonly=False, store=True)
    # text field
    field_path = fields.Char(compute="_compute_field_path", readonly=False, store=True)

    _sql_constraints = [('role_uniq', "unique(campaign_id, role)", "Each campaign should only have one element for each role.")]

    @api.constrains('field_path', 'campaign_id')
    def _check_fields(self):
        skip_security = self.env.su or self.env.user._is_admin()
        for element in self.filtered(lambda e: e.value_type == 'field'):
            RenderModel = self.env[element.res_model]
            field_path = element.field_path
            if not field_path:
                raise exceptions.ValidationError(_("field path must be set on %(element_role)s", element.role))
            try:
                RenderModel.sudo()._mail_map_and_format(field_path)
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

            path_start, dummy, last_field = field_path.rpartition('.')
            # check the last field has a sensible type
            if element.render_type == 'image' and RenderModel.sudo().mapped(path_start)._fields[last_field].type != 'binary':
                raise exceptions.ValidationError(_('%(field_path)s cannot be used as an image value for %(element_role)s', field_path=field_path, element_role=element.role))

    @api.depends('res_model')
    def _compute_value_type(self):
        self.value_type = 'static'

    @api.depends('value_type', 'render_type')
    def _compute_field_path(self):
        for element in self:
            if element.value_type == 'static' or element.render_type == 'image':
                self.field_path = False

    @api.depends('value_type')
    def _compute_image(self):
        for element in self:
            if element.value_type == 'field' or element.render_type == 'text':
                self.image = False

    @api.depends('value_type')
    def _compute_text(self):
        for element in self:
            if element.value_type == 'field' or element.render_type == 'image':
                self.text = False

    @api.depends('value_type')
    def _compute_text_color(self):
        for element in self:
            if element.render_type == 'image':
                self.text_color = False

    def _get_value(self, record):
        """Get the value of the element for a specific record."""
        self.ensure_one()
        if record:
            record.ensure_one()
        if self.value_type == 'field' and record:
            # this will be called with sudo from the controller anyway
            if self.render_type == 'text':
                return record.sudo()._mail_map_and_format(self.field_path) or None
            return record.sudo().mapped(self.field_path)[0]
        if self.render_type == 'image':
            return self.image
        if self.render_type == 'text':
            return self.text
        return None

    def _get_placeholder(self):
        """Placeholder to display in preview mode."""
        if self.value_type == 'field':
            if self.render_type == 'image':
                return base64.b64encode(self.env['ir.binary']._placeholder())
            if self.render_type == 'text':
                return f'[{self.field_path}]'
        return ''
