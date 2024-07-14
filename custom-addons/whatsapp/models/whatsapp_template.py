# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import re
import mimetypes

from markupsafe import Markup

from odoo import api, models, fields, _, Command
from odoo.addons.http_routing.models.ir_http import slugify
from odoo.addons.whatsapp.tools.lang_list import Languages
from odoo.addons.whatsapp.tools.whatsapp_api import WhatsAppApi
from odoo.addons.whatsapp.tools.whatsapp_exception import WhatsAppError
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo.tools import plaintext2html
from odoo.tools.safe_eval import safe_eval

LATITUDE_LONGITUDE_REGEX = r'^[-+]?([1-8]?\d(\.\d+)?|90(\.0+)?),\s*[-+]?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?)$'

COMMON_WHATSAPP_PHONE_SAFE_FIELDS = {
    'mobile',
    'phone',
    'phone_sanitized',
    'partner_id.mobile',
    'partner_id.phone',
    'phone_sanitized.phone',
    'x_studio_mobile',
    'x_studio_phone',
    'x_studio_partner_id.mobile',
    'x_studio_partner_id.phone',
    'x_studio_partner_id.phone_sanitized',
}

class WhatsAppTemplate(models.Model):
    _name = 'whatsapp.template'
    _inherit = ['mail.thread']
    _description = 'WhatsApp Template'
    _order = 'sequence asc, id'

    @api.model
    def _get_default_wa_account_id(self):
        first_account = self.env['whatsapp.account'].search([
            ('allowed_company_ids', 'in', self.env.companies.ids)], limit=1)
        return first_account.id if first_account else False

    @api.model
    def _get_model_selection(self):
        """ Available models are all models, as even transient models could have
        templates associated (e.g. payment.link.wizard) """
        return [
            (model.model, model.name)
            for model in self.env['ir.model'].sudo().search([])
        ]

    name = fields.Char(string="Name", tracking=True)
    template_name = fields.Char(
        string="Template Name",
        compute='_compute_template_name', readonly=False, store=True,
        copy=False)
    sequence = fields.Integer(required=True, default=0)
    active = fields.Boolean(default=True)

    wa_account_id = fields.Many2one(
        comodel_name='whatsapp.account', string="Account", default=_get_default_wa_account_id,
        ondelete="cascade")
    wa_template_uid = fields.Char(string="WhatsApp Template ID", copy=False)
    error_msg = fields.Char(string="Error Message")

    model_id = fields.Many2one(
        string='Applies to', comodel_name='ir.model',
        default=lambda self: self.env['ir.model']._get_id('res.partner'),
        ondelete='cascade', required=True, store=True,
        tracking=1)
    model = fields.Char(
        string='Related Document Model',
        related='model_id.model',
        precompute=True, store=True, readonly=True)
    phone_field = fields.Char(
        string='Phone Field', compute='_compute_phone_field',
        precompute=True, readonly=False, required=True, store=True)
    lang_code = fields.Selection(string="Language", selection=Languages, default='en', required=True)
    template_type = fields.Selection([
        ('authentication', 'Authentication'),
        ('marketing', 'Marketing'),
        ('utility', 'Utility')], string="Category", default='marketing', tracking=True,
        help="Authentication - One-time passwords that your customers use to authenticate a transaction or login.\n"
             "Marketing - Promotions or information about your business, products or services. Or any message that isn't utility or authentication.\n"
             "Utility - Messages about a specific transaction, account, order or customer request.")

    status = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('in_appeal', 'In Appeal'),
        ('approved', 'Approved'),
        ('paused', 'Paused'),
        ('disabled', 'Disabled'),
        ('rejected', 'Rejected'),
        ('pending_deletion', 'Pending Deletion'),
        ('deleted', 'Deleted'),
        ('limit_exceeded', 'Limit Exceeded')], string="Status", default='draft', copy=False, tracking=True)
    quality = fields.Selection([
        ('none', 'None'),
        ('red', 'Red'),
        ('yellow', 'Yellow'),
        ('green', 'Green')], string="Quality", default='none', copy=False, tracking=True)
    allowed_user_ids = fields.Many2many(
        comodel_name='res.users', string="Users",
        domain=[('share', '=', False)])

    body = fields.Text(string="Template body", tracking=True)
    header_type = fields.Selection([
        ('none', 'None'),
        ('text', 'Text'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('document', 'Document'),
        ('location', 'Location')], string="Header Type", default='none')
    header_text = fields.Char(string="Template Header Text", size=60)
    header_attachment_ids = fields.Many2many(
        'ir.attachment', string="Template Static Header",
        copy=False)  # keep False to avoid linking attachments; we have to copy them instead
    footer_text = fields.Char(string="Footer Message")
    report_id = fields.Many2one(
        comodel_name='ir.actions.report', string="Report",
        compute="_compute_report_id", readonly=False, store=True,
        domain="[('model', '=', model)]", tracking=True)
    variable_ids = fields.One2many(
        'whatsapp.template.variable', 'wa_template_id', string="Template Variables",
        store=True, compute='_compute_variable_ids', precompute=True, readonly=False,
        copy=False)  # done with custom code due to buttons variables
    button_ids = fields.One2many(
        'whatsapp.template.button', 'wa_template_id', string="Buttons",
        copy=True)  # will copy their variables

    messages_count = fields.Integer(string="Messages Count", compute='_compute_messages_count')
    has_action = fields.Boolean(string="Has Action", compute='_compute_has_action')

    _sql_constraints = [
        ('unique_name_account_template', 'unique(template_name, lang_code, wa_account_id)', "Duplicate template is not allowed for one Meta account.")
    ]

    @api.constrains('header_text')
    def _check_header_text(self):
        for tmpl in self.filtered(lambda l: l.header_type == 'text'):
            header_variables = list(re.findall(r'{{[1-9][0-9]*}}', tmpl.header_text))
            if len(header_variables) > 1 or (header_variables and header_variables[0] != '{{1}}'):
                raise ValidationError(
                    _("The Header Text must either contain no variable or the first one {{1}}.")
                )

    @api.constrains('phone_field', 'model')
    def _check_phone_field(self):
        is_system = self.user_has_groups('base.group_system')
        for tmpl in self.filtered('phone_field'):
            model = self.env[tmpl.model]
            if not is_system:
                if not model.check_access_rights('read', raise_exception=False):
                    model_description = self.env['ir.model']._get(tmpl.model).display_name
                    raise AccessError(
                        _("You can not select field of %(model)s.", model=model_description)
                    )
                safe_fields = set(COMMON_WHATSAPP_PHONE_SAFE_FIELDS)
                if hasattr(model, '_wa_get_safe_phone_fields'):
                    safe_fields |= set(model._wa_get_safe_phone_fields())
                if tmpl.phone_field not in safe_fields:
                    raise AccessError(
                        _("You are not allowed to use %(field)s in phone field, contact your administrator to configure it.",
                          field=tmpl.phone_field)
                    )
            try:
                model._find_value_from_field_path(tmpl.phone_field)
            except UserError as err:
                raise ValidationError(
                    _("'%(field)s' does not seem to be a valid field path on %(model)s",
                      field=tmpl.phone_field,
                      model=tmpl.model)
                ) from err

    @api.constrains('header_attachment_ids', 'header_type', 'report_id')
    def _check_header_attachment_ids(self):
        templates_with_attachments = self.filtered('header_attachment_ids')
        for tmpl in templates_with_attachments:
            if len(tmpl.header_attachment_ids) > 1:
                raise ValidationError(_('You may only use one header attachment for each template'))
            if tmpl.header_type not in ['image', 'video', 'document']:
                raise ValidationError(_("Only templates using media header types may have header documents"))
            if not any(tmpl.header_attachment_ids.mimetype in mimetypes for mimetypes in self.env['whatsapp.message']._SUPPORTED_ATTACHMENT_TYPE[tmpl.header_type]):
                raise ValidationError(_("File type %(file_type)s not supported for header type %(header_type)s",
                                        file_type=tmpl.header_attachment_ids.mimetype, header_type=tmpl.header_type))
        for tmpl in self - templates_with_attachments:
            if tmpl.header_type == 'document' and not tmpl.report_id:
                raise ValidationError(_("Header document or report is required"))
            if tmpl.header_type in ['image', 'video']:
                raise ValidationError(_("Header document is required"))

    @api.constrains('button_ids', 'variable_ids')
    def _check_buttons(self):
        for tmpl in self:
            if len(tmpl.button_ids) > 10:
                raise ValidationError(_('Maximum 10 buttons allowed.'))
            if len(tmpl.button_ids.filtered(lambda button: button.button_type == 'url')) > 2:
                raise ValidationError(_('Maximum 2 URL buttons allowed.'))
            if len(tmpl.button_ids.filtered(lambda button: button.button_type == 'phone_number')) > 1:
                raise ValidationError(_('Maximum 1 Call Number button allowed.'))

    @api.constrains('variable_ids')
    def _check_body_variables(self):
        for template in self:
            variables = template.variable_ids.filtered(lambda variable: variable.line_type == 'body')
            free_text_variables = variables.filtered(lambda variable: variable.field_type == 'free_text')
            if len(free_text_variables) > 10:
                raise ValidationError(_('Only 10 free text is allowed in body of template'))

            variable_indices = sorted(var._extract_variable_index() for var in variables)
            if len(variable_indices) > 0 and (variable_indices[0] != 1 or variable_indices[-1] != len(variables)):
                missing = next(
                    (index for index in range(1, len(variables)) if variable_indices[index - 1] + 1 != variable_indices[index]),
                    0) + 1
                raise ValidationError(_('Body variables should start at 1 and not skip any number, missing %d', missing))

    @api.constrains('header_type', 'variable_ids')
    def _check_header_variables(self):
        for template in self:
            location_vars = template.variable_ids.filtered(lambda var: var.line_type == 'location')
            text_vars = template.variable_ids.filtered(lambda var: var.line_type == 'header')
            if template.header_type == 'location' and len(location_vars) != 4:
                raise ValidationError(_('When using a "location" header, there should 4 location variables not %(count)d.',
                                        count=len(location_vars)))
            elif template.header_type != 'location' and location_vars:
                raise ValidationError(_('Location variables should only exist when a "location" header is selected.'))
            if len(text_vars) > 1:
                raise ValidationError(_('There should be at most 1 variable in the header of the template.'))
            if text_vars and text_vars._extract_variable_index() != 1:
                raise ValidationError(_('Free text variable in the header should be {{1}}'))

    #=====================================================
    #                 Compute Methods
    #=====================================================

    @api.depends('model')
    def _compute_phone_field(self):
        to_reset = self.filtered(lambda template: not template.model)
        if to_reset:
            to_reset.phone_field = False
        for template in self.filtered('model'):
            if template.phone_field and template.phone_field in self.env[template.model]._fields:
                continue
            if 'mobile' in self.env[template.model]._fields:
                template.phone_field = 'mobile'
            elif 'phone' in self.env[template.model]._fields:
                template.phone_field = 'phone'

    @api.depends('name', 'status', 'wa_template_uid')
    def _compute_template_name(self):
        for template in self:
            if not template.template_name or (template.status == 'draft' and not template.wa_template_uid):
                template.template_name = re.sub(r'\W+', '_', slugify(template.name or ''))

    @api.depends('model')
    def _compute_model_id(self):
        self.filtered(lambda tpl: not tpl.model).model_id = False
        for template in self.filtered('model'):
            template.model_id = self.env['ir.model']._get_id(template.model)

    @api.depends('model')
    def _compute_report_id(self):
        """ Reset if model changes to avoid ill defined reports """
        to_reset = self.filtered(lambda tpl: tpl.report_id.model != tpl.model)
        if to_reset:
            to_reset.report_id = False

    @api.depends('header_type', 'header_text', 'body')
    def _compute_variable_ids(self):
        """compute template variable according to header text, body and buttons"""
        for tmpl in self:
            to_delete = self.env["whatsapp.template.variable"]
            to_keep = self.env["whatsapp.template.variable"]
            to_create_values = []

            header_variables = list(re.findall(r'{{[1-9][0-9]*}}', tmpl.header_text or ''))
            body_variables = set(re.findall(r'{{[1-9][0-9]*}}', tmpl.body or ''))

            # if there is header text
            existing_header_text_variable = tmpl.variable_ids.filtered(lambda line: line.line_type == 'header')
            if header_variables and not existing_header_text_variable:
                to_create_values.append({'name': header_variables[0], 'line_type': 'header', 'wa_template_id': tmpl.id})
            elif not header_variables and existing_header_text_variable:
                to_delete += existing_header_text_variable
            elif existing_header_text_variable:
                to_keep += existing_header_text_variable

            # if the header is a location
            existing_header_location_variables = tmpl.variable_ids.filtered(lambda line: line.line_type == 'location')
            if tmpl.header_type == 'location' and not existing_header_location_variables:
                to_create_values += [
                    {'name': 'name', 'line_type': 'location', 'wa_template_id': tmpl.id},
                    {'name': 'address', 'line_type': 'location', 'wa_template_id': tmpl.id},
                    {'name': 'latitude', 'line_type': 'location', 'wa_template_id': tmpl.id},
                    {'name': 'longitude', 'line_type': 'location', 'wa_template_id': tmpl.id}
                ]
            elif tmpl.header_type != 'location' and existing_header_location_variables:
                to_delete += existing_header_location_variables
            elif existing_header_location_variables:
                to_keep += existing_header_location_variables

            # body
            existing_body_variables = tmpl.variable_ids.filtered(lambda line: line.line_type == 'body')
            new_body_variable_names = [var_name for var_name in body_variables if var_name not in existing_body_variables.mapped('name')]
            deleted_body_variables = existing_body_variables.filtered(lambda var: var.name not in body_variables)

            to_create_values += [{'name': var_name, 'line_type': 'body', 'wa_template_id': tmpl.id} for var_name in set(new_body_variable_names)]
            to_delete += deleted_body_variables
            to_keep += existing_body_variables - deleted_body_variables

            # if to_delete:
            #     to_delete.unlink()
            tmpl.variable_ids = [(3, to_remove.id) for to_remove in to_delete] + [(0, 0, vals) for vals in to_create_values]

    @api.depends('model_id')
    def _compute_has_action(self):
        for tmpl in self:
            action = self.env['ir.actions.act_window'].sudo().search([('res_model', '=', 'whatsapp.composer'), ('binding_model_id', '=', tmpl.model_id.id)])
            if action:
                tmpl.has_action = True
            else:
                tmpl.has_action = False

    def _compute_messages_count(self):
        messages_by_template = dict(self.env['whatsapp.message']._read_group(
            [('wa_template_id', 'in', self.ids)],
            groupby=['wa_template_id'],
            aggregates=['__count'],
        ))
        for tmpl in self:
            tmpl.messages_count = messages_by_template.get(tmpl, 0)

    @api.depends('name', 'wa_account_id')
    def _compute_display_name(self):
        for template in self:
            template.display_name = _('%(template_name)s [%(account_name)s]',
                                        template_name=template.name,
                                        account_name=template.wa_account_id.name
                                    ) if template.wa_account_id.name else template.name

    @api.onchange('header_type')
    def _onchange_header_type(self):
        toreset_attachments = self.filtered(lambda t: t.header_type not in {"image", "video", "document"})
        if toreset_attachments:
            toreset_attachments.header_attachment_ids = [(5, 0)]
            toreset_attachments.report_id = False
        toreset_text = self.filtered(lambda t: t.header_type != "text")
        if toreset_text:
            toreset_text.header_text = False

    @api.onchange('header_attachment_ids')
    def _onchange_header_attachment_ids(self):
        for template in self:
            template.header_attachment_ids.res_id = template.id
            template.header_attachment_ids.res_model = template._name

    @api.onchange('wa_account_id')
    def _onchange_wa_account_id(self):
        """Avoid carrying remote sync data when changing account."""
        self.status = 'draft'
        self.quality = 'none'
        self.wa_template_uid = False

    #===================================================================
    #                 CRUD
    #===================================================================

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # stable backward compatible change  for model fields
            if vals.get('model_id'):
                vals['model'] = self.env['ir.model'].sudo().browse(vals[('model_id')]).model
        records = super().create(vals_list)
        # the model of the variable might have been changed with x2many commands
        records.variable_ids._check_field_name()
        # update the attachment res_id for new records
        records._onchange_header_attachment_ids()
        return records

    def write(self, vals):
        if vals.get("model_id"):
            vals["model"] = self.env['ir.model'].sudo().browse(vals["model_id"]).model
        res = super().write(vals)
        # Model change: explicitly check for field access. Other changes at variable
        # level are checked by '_check_field_name' constraint.
        if 'model_id' in vals:
            self.variable_ids._check_field_name()
        return res

    def copy_data(self, default=None):
        default = {} if default is None else default
        if not default.get('name'):
            default['name'] = _('%(original_name)s (copy)', original_name=self.name)
        if not default.get('template_name'):
            default['template_name'] = f'{self.template_name}_copy'

        values = super().copy_data(default=default)
        if values and values[0] and self.header_attachment_ids and not values[0].get('header_attachment_ids'):
            values[0]['header_attachment_ids'] = [
                (0, 0, att.copy_data(default={'res_id': False})[0])
                for att in self.header_attachment_ids
            ]
        if values and values[0] and self.variable_ids:
            variable_commands = values[0].get('variable_ids', []) + [
                (0, 0, {
                    'button_id': False,
                    'demo_value': variable.demo_value,
                    'field_name': variable.field_name,
                    'field_type': variable.field_type,
                    'line_type': variable.line_type,
                    'name': variable.name,
                })
                for variable in self.variable_ids if not variable.button_id
            ]
            if variable_commands:
                values[0]['variable_ids'] = variable_commands
        return values

    #===================================================================
    #                 Register template to whatsapp
    #===================================================================

    def _get_template_head_component(self, file_handle):
        """Return header component according to header type for template registration to whatsapp"""
        if self.header_type == 'none':
            return None
        head_component = {'type': 'HEADER', 'format': self.header_type.upper()}
        if self.header_type == 'text' and self.header_text:
            head_component['text'] = self.header_text
            header_params = self.variable_ids.filtered(lambda line: line.line_type == 'header')
            if header_params:
                head_component['example'] = {'header_text': header_params.mapped('demo_value')}
        elif self.header_type in ['image', 'video', 'document']:
            head_component['example'] = {
                'header_handle': [file_handle]
            }
        return head_component

    def _get_template_body_component(self):
        """Return body component for template registration to whatsapp"""
        if not self.body:
            return None
        body_component = {'type': 'BODY', 'text': self.body}
        body_params = self.variable_ids.filtered(lambda line: line.line_type == 'body')
        if body_params:
            body_component['example'] = {'body_text': [body_params.mapped('demo_value')]}
        return body_component

    def _get_template_button_component(self):
        """Return button component for template registration to whatsapp"""
        if not self.button_ids:
            return None
        buttons = []
        for button in self.button_ids:
            button_data = {
                'type': button.button_type.upper(),
                'text': button.name
            }
            if button.button_type == 'url':
                button_data['url'] = button.website_url
                if button.url_type == 'dynamic':
                    button_data['url'] += '{{1}}'
                    button_data['example'] = button.variable_ids[0].demo_value
            elif button.button_type == 'phone_number':
                button_data['phone_number'] = button.call_number
            buttons.append(button_data)
        return {'type': 'BUTTONS', 'buttons': buttons}

    def _get_template_footer_component(self):
        if not self.footer_text:
            return None
        return {'type': 'FOOTER', 'text': self.footer_text}

    def _get_sample_record(self):
        return self.env[self.model].search([], limit=1)

    def button_submit_template(self):
        """Register template to WhatsApp Business Account """
        self.ensure_one()
        wa_api = WhatsAppApi(self.wa_account_id)
        attachment = False
        if self.header_type in ('image', 'video', 'document'):
            if self.header_type == 'document' and self.report_id:
                record = self._get_sample_record()
                if not record:
                    raise ValidationError(_("There is no record for preparing demo pdf in model %(model)s", model=self.model_id.name))
                attachment = self._generate_attachment_from_report(record)
            else:
                attachment = self.header_attachment_ids
            if not attachment:
                raise ValidationError("Header Document is missing")
        file_handle = False
        if attachment:
            try:
                file_handle = wa_api._upload_demo_document(attachment)
            except WhatsAppError as e:
                raise UserError(str(e))

        components = [self._get_template_body_component()]
        components += [comp for comp in (
            self._get_template_head_component(file_handle),
            self._get_template_button_component(),
            self._get_template_footer_component()) if comp]
        json_data = json.dumps({
            'name': self.template_name,
            'language': self.lang_code,
            'category': self.template_type.upper(),
            'components': components,
        })
        try:
            if self.wa_template_uid:
                wa_api._submit_template_update(json_data, self.wa_template_uid)
                self.status = 'pending'
            else:
                response = wa_api._submit_template_new(json_data)
                self.write({
                    'wa_template_uid': response['id'],
                    'status': response['status'].lower()
                })
        except WhatsAppError as we:
            raise UserError(str(we))

    #===================================================================
    #                 Sync template from whatsapp
    #===================================================================

    def button_sync_template(self):
        """Sync template from WhatsApp Business Account """
        self.ensure_one()
        wa_api = WhatsAppApi(self.wa_account_id)
        try:
            response = wa_api._get_template_data(wa_template_uid=self.wa_template_uid)
        except WhatsAppError as e:
            raise ValidationError(str(e))
        if response.get('id'):
            self._update_template_from_response(response)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.model
    def _create_template_from_response(self, remote_template_vals, wa_account):
        template_vals = self._get_template_vals_from_response(remote_template_vals, wa_account)
        template_vals['variable_ids'] = [Command.create(var) for var in template_vals['variable_ids']]
        for button in template_vals['button_ids']:
            button['variable_ids'] = [Command.create(var) for var in button['variable_ids']]
        template_vals['button_ids'] = [Command.create(button) for button in template_vals['button_ids']]
        template_vals['header_attachment_ids'] = [Command.create(attachment) for attachment in template_vals['header_attachment_ids']]
        return template_vals

    def _update_template_from_response(self, remote_template_vals):
        self.ensure_one()
        update_fields = ('body', 'header_type', 'header_text', 'footer_text', 'lang_code', 'template_type', 'status')
        template_vals = self._get_template_vals_from_response(remote_template_vals, self.wa_account_id)
        update_vals = {field: template_vals[field] for field in update_fields}

        # variables should be preserved instead of overwritten to keep odoo-specific data like fields
        variable_ids = []
        existing_template_variables = {(variable_id.name, variable_id.line_type): variable_id.id for variable_id in self.variable_ids}
        for variable_vals in template_vals['variable_ids']:
            if not existing_template_variables.pop((variable_vals['name'], variable_vals['line_type']), False):
                variable_ids.append(Command.create(variable_vals))
        variable_ids.extend([Command.delete(to_remove) for to_remove in existing_template_variables.values()])
        update_vals['variable_ids'] = variable_ids

        for button in template_vals['button_ids']:
            button['variable_ids'] = [Command.create(var) for var in button['variable_ids']]
        update_vals['button_ids'] = [Command.clear()] + [Command.create(button) for button in template_vals['button_ids']]

        if not self.header_attachment_ids or self.header_type != template_vals['header_type']:
            new_attachment_commands = [Command.create(attachment) for attachment in template_vals['header_attachment_ids']]
            update_vals['header_attachment_ids'] = [Command.clear()] + new_attachment_commands

        self.write(update_vals)

    def _get_template_vals_from_response(self, remote_template_vals, wa_account):
        """Get dictionary of field: values from whatsapp template response json.

        Relational fields will use arrays instead of commands.
        """
        template_vals = {
            'body': False,
            'button_ids': [],
            'footer_text': False,
            'header_text': False,
            'header_attachment_ids': [],
            'header_type': 'none',
            'lang_code': remote_template_vals['language'],
            'name': remote_template_vals['name'].replace("_", " ").title(),
            'status': remote_template_vals['status'].lower(),
            'template_name': remote_template_vals['name'],
            'template_type': remote_template_vals['category'].lower(),
            'variable_ids': [],
            'wa_account_id': wa_account.id,
            'wa_template_uid': int(remote_template_vals['id']),
        }
        for component in remote_template_vals['components']:
            component_type = component['type']
            if component_type == 'HEADER':
                template_vals['header_type'] = component['format'].lower()
                if component['format'] == 'TEXT':
                    template_vals['header_text'] = component['text']
                    if 'example' in component:
                        for index, example_value in enumerate(component['example'].get('header_text', [])):
                            template_vals['variable_ids'].append({
                                'name': '{{%s}}' % (index + 1),
                                'demo_value': example_value,
                                'line_type': 'header',
                            })
                elif component['format'] == 'LOCATION':
                    for location_val in ['name', 'address', 'latitude', 'longitude']:
                        template_vals['variable_ids'].append({
                            'name': location_val,
                            'line_type': 'location',
                        })
                elif component['format'] in ('IMAGE', 'VIDEO', 'DOCUMENT'):
                    document_url = component.get('example', {}).get('header_handle', [False])[0]
                    if document_url:
                        wa_api = WhatsAppApi(wa_account)
                        data, mimetype = wa_api._get_header_data_from_handle(document_url)
                        extension = mimetypes.guess_extension(mimetype)
                    else:
                        data = b'AAAA'
                        extension, mimetype = {
                            'IMAGE': ('jpg', 'image/jpeg'),
                            'VIDEO': ('mp4', 'video/mp4'),
                            'DOCUMENT': ('pdf', 'application/pdf')
                        }[component['format']]
                    template_vals['header_attachment_ids'] = [{
                        'name': f'{template_vals["template_name"]}{extension}',
                        'res_model': self._name,
                        'res_id': self.ids[0] if self else False,
                        'raw': data,
                        'mimetype': mimetype,
                    }]
            elif component_type == 'BODY':
                template_vals['body'] = component['text']
                if 'example' in component:
                    for index, example_value in enumerate(component['example'].get('body_text', [[]])[0]):
                        template_vals['variable_ids'].append({
                            'name': '{{%s}}' % (index + 1),
                            'demo_value': example_value,
                            'line_type': 'body',
                        })
            elif component_type == 'FOOTER':
                template_vals['footer_text'] = component['text']
            elif component_type == 'BUTTONS':
                for index, button in enumerate(component['buttons']):
                    if button['type'] in ('URL', 'PHONE_NUMBER', 'QUICK_REPLY'):
                        button_vals = {
                            'sequence': index,
                            'name': button['text'],
                            'button_type': button['type'].lower(),
                            'call_number': button.get('phone_number'),
                            'website_url': button.get('url').replace('{{1}}', '') if button.get('url') else None,
                            'url_type': button.get('example', []) and 'dynamic' or 'static',
                            'variable_ids': []
                        }
                        for example_index, example_value in enumerate(button.get('example', [])):
                            button_vals['variable_ids'].append({
                                'name': '{{%s}}' % (example_index + 1),
                                'demo_value': example_value,
                                'line_type': 'button',
                            })
                        template_vals['button_ids'].append(button_vals)
        return template_vals

    #========================================================================
    #         Send WhatsApp message using template
    #========================================================================

    def _get_header_component(self, free_text_json, template_variables_value, attachment):
        """ Prepare header component for sending WhatsApp template message"""
        header = []
        header_type = self.header_type
        if header_type == 'text' and template_variables_value.get('header-{{1}}'):
            value = (free_text_json or {}).get('header_text') or template_variables_value.get('header-{{1}}') or ' '
            header = {
                'type': 'header',
                'parameters': [{'type': 'text', 'text': value}]
            }
        elif header_type in ['image', 'video', 'document']:
            header = {
                'type': 'header',
                'parameters': [self.env['whatsapp.message']._prepare_attachment_vals(attachment, wa_account_id=self.wa_account_id)]
            }
        elif header_type == 'location':
            header = {
                'type': 'header',
                'parameters': [self._prepare_location_vals(template_variables_value)]
            }
        return header

    def _prepare_location_vals(self, template_variables_value):
        """ Prepare location values for sending WhatsApp template message having header type location"""
        self._check_location_latitude_longitude(template_variables_value.get('location-latitude'), template_variables_value.get('location-longitude'))
        return {
            'type': 'location',
            'location': {
                'name': template_variables_value.get('location-name'),
                'address': template_variables_value.get('location-address'),
                'latitude': template_variables_value.get('location-latitude'),
                'longitude': template_variables_value.get('location-longitude'),
            }
        }

    def _get_body_component(self, free_text_json, template_variables_value):
        """ Prepare body component for sending WhatsApp template message"""
        if not self.variable_ids:
            return None
        parameters = []
        free_text_count = 1
        for body_val in self.variable_ids.filtered(lambda line: line.line_type == 'body'):
            free_text_value = body_val.field_type == 'free_text' and free_text_json.get(f'free_text_{free_text_count}') or False
            parameters.append({
                'type': 'text',
                'text': free_text_value or template_variables_value.get(f'{body_val.line_type}-{body_val.name}') or ' '
            })
            if body_val.field_type == 'free_text':
                free_text_count += 1
        return {'type': 'body', 'parameters': parameters}

    def _get_button_components(self, free_text_json, template_variables_value):
        """ Prepare button component for sending WhatsApp template message"""
        components = []
        if not self.variable_ids:
            return components
        dynamic_buttons = self.button_ids.filtered(lambda line: line.url_type == 'dynamic')
        dynamic_index = {button: i for i, button in enumerate(self.button_ids)}
        free_text_index = 1
        for button in dynamic_buttons:
            button_var = button.variable_ids[0]
            dynamic_url = button.website_url
            if button_var.field_type == 'free_text':
                value = free_text_json.get(f'button_dynamic_url_{free_text_index}') or ' '
                free_text_index += 1
            else:
                value = template_variables_value.get(f'button-{button.name}') or ' '
            value = value.replace(dynamic_url, '').lstrip('/')  # / is implicit
            components.append({
                'type': 'button',
                'sub_type': 'url',
                'index': dynamic_index.get(button),
                'parameters': [{'type': 'text', 'text': value}]
            })
        return components

    def _get_send_template_vals(self, record, free_text_json, attachment=False):
        """Prepare JSON dictionary for sending WhatsApp template message"""
        self.ensure_one()
        components = []
        template_variables_value = self.variable_ids._get_variables_value(record)

        # generate attachment
        if not attachment and self.report_id:
            attachment = self._generate_attachment_from_report(record)
        if not attachment and self.header_attachment_ids:
            attachment = self.header_attachment_ids[0]

        # generate content
        header = self._get_header_component(free_text_json=free_text_json, attachment=attachment, template_variables_value=template_variables_value)
        body = self._get_body_component(free_text_json=free_text_json, template_variables_value=template_variables_value)
        buttons = self._get_button_components(free_text_json=free_text_json, template_variables_value=template_variables_value)
        if header:
            components.append(header)
        if body:
            components.append(body)
        components.extend(buttons)
        template_vals = {
            'name': self.template_name,
            'language': {'code': self.lang_code},
        }
        if components:
            template_vals['components'] = components
        return template_vals, attachment

    def button_reset_to_draft(self):
        for tmpl in self:
            tmpl.write({'status': 'draft'})

    def action_open_messages(self):
        self.ensure_one()
        return {
            'name': _("Message Statistics Of %(template_name)s", template_name=self.name),
            'view_mode': 'tree,form',
            'res_model': 'whatsapp.message',
            'domain': [('wa_template_id', '=', self.id)],
            'type': 'ir.actions.act_window',
        }

    def button_create_action(self):
        """ Create action for sending WhatsApp template message in model defined in template. It will be used in bulk sending"""
        self.check_access_rule('write')
        actions = self.env['ir.actions.act_window'].sudo().search([
            ('res_model', '=', 'whatsapp.composer'),
            ('binding_model_id', 'in', self.model_id.ids)
        ])
        self.env['ir.actions.act_window'].sudo().create([
            {
                'binding_model_id': model.id,
                'name': _('WhatsApp Message'),
                'res_model': 'whatsapp.composer',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
            }
            for model in (self.model_id - actions.binding_model_id)
        ])

    def button_delete_action(self):
        self.check_access_rule('write')
        self.env['ir.actions.act_window'].sudo().search([
            ('res_model', '=', 'whatsapp.composer'),
            ('binding_model_id', 'in', self.model_id.ids)
        ]).unlink()

    def _generate_attachment_from_report(self, record=False):
        """Create attachment from report if relevant"""
        if record and self.header_type == 'document' and self.report_id:
            report_content, report_format = self.report_id._render_qweb_pdf(self.report_id, record.id)
            if self.report_id.print_report_name:
                report_name = safe_eval(self.report_id.print_report_name, {'object': record}) + '.' + report_format
            else:
                report_name = self.display_name + '.' + report_format
            return self.env['ir.attachment'].create({
                'name': report_name,
                'raw': report_content,
                'mimetype': 'application/pdf',
            })
        return self.env['ir.attachment']

    def _check_location_latitude_longitude(self, latitude, longitude):
        if not re.match(LATITUDE_LONGITUDE_REGEX, f"{latitude}, {longitude}"):
            raise ValidationError(
                _("Location Latitude and Longitude %(latitude)s / %(longitude)s is not in proper format.",
                  latitude=latitude, longitude=longitude)
            )

    @api.model
    def _format_markup_to_html(self, body_html):
        """
            Convert WhatsApp format text to HTML format text
            *bold* -> <b>bold</b>
            _italic_ -> <i>italic</i>
            ~strikethrough~ -> <s>strikethrough</s>
            ```monospace``` -> <code>monospace</code>
        """
        formatted_body = str(plaintext2html(body_html))  # stringify for regex
        formatted_body = re.sub(r'\*(.*?)\*', r'<b>\1</b>', formatted_body)
        formatted_body = re.sub(r'_(.*?)_', r'<i>\1</i>', formatted_body)
        formatted_body = re.sub(r'~(.*?)~', r'<s>\1</s>', formatted_body)
        formatted_body = re.sub(r'```(.*?)```', r'<code>\1</code>', formatted_body)
        return Markup(formatted_body)

    def _get_formatted_body(self, demo_fallback=False, variable_values=None):
        """Get formatted body and header with specified values.

        :param bool demo_fallback: if true, fallback on demo values instead of blanks
        :param dict variable_values: values to use instead of demo values {'header-{{1}}': 'Hello'}
        :return Markup:
        """
        self.ensure_one()
        variable_values = variable_values or {}
        header = ''
        if self.header_type == 'text' and self.header_text:
            header = self.header_text
            header_variables = self.variable_ids.filtered(lambda line: line.line_type == 'header')
            if header_variables:
                fallback_value = header_variables[0].demo_value if demo_fallback else ' '
                header = header.replace('{{1}}', variable_values.get('header-{{1}}', fallback_value))
        body = self.body
        for var in self.variable_ids.filtered(lambda var: var.line_type == 'body'):
            fallback_value = var.demo_value if demo_fallback else ' '
            body = body.replace(var.name, variable_values.get(f'{var.line_type}-{var.name}', fallback_value))
        return self._format_markup_to_html(f'*{header}*\n\n{body}' if header else body)


    # ------------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------------

    @api.model
    def _can_use_whatsapp(self, model_name):
        return self.env.user.has_group('whatsapp.group_whatsapp_admin') or \
            bool(self._find_default_for_model(model_name))

    @api.model
    def _find_default_for_model(self, model_name):
        return self.search([
            ('model', '=', model_name),
            ('status', '=', 'approved'),
            '|',
                ('allowed_user_ids', '=', False),
                ('allowed_user_ids', 'in', self.env.user.ids)
        ], limit=1)
