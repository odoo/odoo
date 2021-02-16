# Copyright Nova Code (http://www.novacode.nl)
# See LICENSE file for full licensing details.

import ast
import json
import re
import uuid

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.http import request

from ..utils import get_field_selection_label

STATE_DRAFT = 'DRAFT'
STATE_CURRENT = 'CURRENT'
STATE_OBSOLETE = 'OBSOLETE'

STATES = [
    (STATE_DRAFT, "Draft"),
    (STATE_CURRENT, "Current"),
    (STATE_OBSOLETE, "Obsolete")]


class Builder(models.Model):
    _name = 'formio.builder'
    _description = 'Form Builder'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    _rec_name = 'display_name_full'

    _interval_selection = {'minutes': 'Minutes', 'hours': 'Hours', 'days': 'Days'}

    name = fields.Char(
        "Name", required=True, tracking=True,
        help="""Identifies this specific form. This name can be used in APIs. \
        Use only ASCII letters, digits, "-" or "_".""")
    uuid = fields.Char(
        default=lambda self: self._default_uuid(), required=True, readonly=True, copy=False,
        string='UUID')
    title = fields.Char(
        "Title", required=True,
        help="The form title in the current language", tracking=True)
    description = fields.Text("Description")
    formio_version_id = fields.Many2one(
        'formio.version', string='Form.io Version', required=True,
        default=lambda self: self._default_formio_version_id(), tracking=True,
        help="""Loads the specific Form.io Javascript API/libraries version (sourcecode: \https://github.com/formio/formio.js)""")
    formio_version_name = fields.Char(related='formio_version_id.name', string='Form.io version', tracking=False) # silly, but avoids duplicate tracking message
    formio_css_assets = fields.One2many(related='formio_version_id.css_assets', string='Form.io CSS')
    formio_js_assets = fields.One2many(related='formio_version_id.js_assets', string='Form.io Javascript')
    formio_js_options_id = fields.Many2one('formio.builder.js.options', string='Form.io Javascript Options template', store=False)
    formio_js_options = fields.Text(
        default=lambda self: self._default_formio_js_options(),
        string='Form.io Javascript Options')
    res_model_id = fields.Many2one(
        "ir.model", compute='_compute_res_model_id', store=True,
        string="Model", help="Model as resource this form represents or acts on")
    res_model = fields.Char(compute='_compute_res_model_id', store=True)
    formio_res_model_id = fields.Many2one(
        "formio.res.model",
        string="Resource Model",
        ondelete='restrict', tracking=True,
        help="Model as resource this form represents or acts on")
    schema = fields.Text("JSON Schema")
    edit_url = fields.Char(compute='_compute_edit_url', readonly=True)
    act_window_url = fields.Char(compute='_compute_act_window_url', readonly=True)
    state = fields.Selection(
        selection=STATES, string="State",
        default=STATE_DRAFT, required=True, tracking=True,
        help="""\
        - Draft: In draft / design.
        - Current: Live and in use (publisehd).
        - Obsolete: Was current but obsolete (unpublished)""")
    display_state = fields.Char("Display State", compute='_compute_display_fields', store=False)
    display_name_full = fields.Char("Display Name Full", compute='_compute_display_fields', store=False)
    parent_id = fields.Many2one('formio.builder', string='Parent Builder', readonly=True)
    parent_version = fields.Integer(related='parent_id.version', string='Parent Version', readonly=True)
    version = fields.Integer("Version", required=True, readonly=True, default=1)
    version_comment = fields.Text("Version Comment")
    user_id = fields.Many2one('res.users', string='Assigned user', tracking=True)
    forms = fields.One2many('formio.form', 'builder_id', string='Forms')
    portal = fields.Boolean("Portal", tracking=True, help="Form is accessible by assigned portal user")
    portal_submit_done_url = fields.Char(
        string='Portal Submit-done URL', tracking=True,
        help="""\
        IMPORTANT:
        - Absolute URL should contain a protocol (https://, http://)
        - Relative URL is also supported e.g. /web/login
        """
    )
    public = fields.Boolean("Public", tracking=True, help="Form is public accessible (e.g. used in Shop checkout, Events registration")
    public_url = fields.Char(string='Public URL', compute='_compute_public_url', store=True, copy=False)
    public_submit_done_url = fields.Char(
        string='Public Submit-done URL', tracking=True,
        help="""\
        IMPORTANT:
        - Absolute URL should contain a protocol (https://, http://)
        - Relative URL is also supported e.g. /web/login
        """
    )
    public_access_interval_number = fields.Integer(default=30, tracking=True, help="Public access to submitted Form shall be rejected after expiration of the configured time interval.")
    public_access_interval_type = fields.Selection(list(_interval_selection.items()), default='minutes', tracking=True)
    view_as_html = fields.Boolean("View as HTML", tracking=True, help="View submission as a HTML view instead of disabled webform.")
    show_form_title = fields.Boolean("Show Form Title", tracking=True, help="Show Form Title in the Form header.", default=True)
    show_form_id = fields.Boolean("Show Form ID", tracking=True, help="Show Form ID in the Form header.", default=True)
    show_form_uuid = fields.Boolean("Show Form UUID", tracking=True, help="Show Form UUID in the Form.", default=True)
    show_form_state = fields.Boolean("Show Form State", tracking=True, help="Show the state in the Form header.", default=True)
    show_form_user_metadata = fields.Boolean(
        "Show User Metadata", tracking=True, help="Show submission and assigned user metadata in the Form header.", default=True)
    wizard = fields.Boolean("Wizard", tracking=True)
    translations = fields.One2many('formio.builder.translation', 'builder_id', string='Translations')
    languages = fields.One2many('res.lang', compute='_compute_languages', string='Languages')
    allow_force_update_state_group_ids = fields.Many2many(
        'res.groups', string='Allow groups to force update State',
        help="User groups allowed to manually force an update of the Form state."
             "If no groups are specified it's allowed for every user.")
    language_en_enable = fields.Boolean(default=True, string='English Enabled')
    component_partner_name = fields.Char(string='Component Partner Name', tracking=True)
    component_partner_email = fields.Char(string='Component Partner Email', tracking=True)
    component_partner_add_follower = fields.Boolean(
        string='Component Partner Add to Followers', tracking=True, help='Add determined partner to followers of the Form.')
    component_partner_activity_user_id = fields.Many2one('res.users', tracking=True)
    form_allow_copy = fields.Boolean(string='Allow Copies', help='Allow copying form submissions.', tracking=True, default=True)
    form_copy_to_current = fields.Boolean(string='Copy To Current', help='When copying a form, always link it to the current version of the builder instead of the original builder.', tracking=True, default=True)

    def _states_selection(self):
        return STATES

    @api.model
    def _default_uuid(self):
        return str(uuid.uuid4())

    @api.model
    def _default_formio_version_id(self):
        Param = self.env['ir.config_parameter'].sudo()
        default_version = Param.get_param('formio.default_version')
        if default_version:
            domain = [('name', '=', default_version)]
            version = self.env['formio.version'].search(domain, limit=1)
            if version:
                return version.id
            else:
                return False
        else:
            return False

    @api.model
    def _default_formio_js_options(self):
        Param = self.env['ir.config_parameter'].sudo()
        default_builder_js_options_id = Param.get_param('formio.default_builder_js_options_id')
        builder_js_options = self.env['formio.builder.js.options'].browse(int(default_builder_js_options_id))
        return builder_js_options.value

    @api.constrains('name')
    def constaint_check_name(self):
        self.ensure_one
        if re.search(r"[^a-zA-Z0-9_-]", self.name) is not None:
            raise ValidationError('Name is invalid. Use ASCII letters, digits, "-" or "_".')

    @api.constrains("name", "state")
    def constraint_one_current(self):
        """ Per name there can be only 1 record with state current at
        a time. """

        res = self.search([
            ("name", "=", self.name),
            ("state", "=", STATE_CURRENT)
            ])
        if len(res) > 1:
            msg = _('Only one Form Builder with name "{name}" can be in state Current.').format(
                name=self.name)
            raise ValidationError(msg)

    @api.constrains("name", "version")
    def constraint_one_version(self):
        """ Per name there can be only 1 record with same version at a
        time. """

        domain = [('name', '=', self.name), ('version', '=', self.version)]
        res = self.search_count(domain)
        if res > 1:
            raise ValidationError("%s already has a record with version: %d. Use button/action: Create New Version."
                                  % (self.name, self.version))

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        name_suffix = fields.Datetime.to_string(fields.Datetime.now())
        name_suffix = name_suffix.replace(' ', '_')
        name_suffix = name_suffix.replace(':', '-')

        default = default or {}
        default['name'] = '%s_%s' % (self.name, name_suffix)
        return super(Builder, self).copy(default=default)

    def _decode_schema(self, schema):
        """ Convert schema (str) to dictionary

        json.loads(data) refuses identifies with single quotes.Use
        ast.literal_eval() instead.
        
        :param str schema: schema string
        :return str schema: schema as dictionary
        """
        try:
            schema = json.loads(schema)
        except:
            schema = ast.literal_eval(schema)
        return schema

    @api.onchange('formio_js_options_id')
    def _onchange_formio_js_options_id(self):
        if self.formio_js_options_id:
            self.formio_js_options = self.formio_js_options_id.value

    @api.onchange('wizard')
    def _onchange_wizard(self):
        if self.wizard:
            if self.schema:
                schema = self._decode_schema(self.schema)
                schema['display'] = "wizard"
                self.schema = json.dumps(schema)
            else:
                self.schema = '{"display": "wizard"}'
        else:
            if self.schema:
                schema = self._decode_schema(self.schema)
                del schema['display']
                self.schema = json.dumps(schema)

    @api.depends('formio_res_model_id')
    def _compute_res_model_id(self):
        for r in self:
            if r.formio_res_model_id:
                r.res_model_id = r.formio_res_model_id.ir_model_id.id
                r.res_model = r.formio_res_model_id.ir_model_id.model
            else:
                r.res_model_id = False
                r.res_model = False

    @api.depends('title', 'name', 'version', 'state')
    def _compute_display_fields(self):
        for r in self:
            r.display_state = get_field_selection_label(r, 'state')
            if self._context.get('display_name_title'):
                r.display_name_full = r.title
            else:
                r.display_name_full = _("{title} (state: {state} - version: {version})").format(
                    title=r.title, state=r.display_state, version=r.version)

    @api.depends('public')
    def _compute_public_url(self):
        for r in self:
            if r.public and request:
                url_root = request.httprequest.url_root
                self.public_url = '%s%s/%s' % (url_root, 'formio/public/form/create', r.uuid)
            else:
                r.public_url = False

    @api.depends('translations')
    def _compute_languages(self):
        for r in self:
            languages = r.translations.mapped('lang_id')
            lang_en = self.env.ref('base.lang_en')
            if lang_en.active and r.language_en_enable and 'en_US' not in languages.mapped('code'):
                languages |= lang_en
            r.languages = languages.sorted('name')

    def _compute_edit_url(self):
        # sudo() is needed for regular users.
        for r in self:
            url = '{base_url}/formio/builder/{builder_id}'.format(
                base_url=self.env['ir.config_parameter'].sudo().get_param('web.base.url'),
                builder_id=r.id)
            r.edit_url = url

    def _compute_act_window_url(self):
        for r in self:
            action = self.env.ref('formio.action_formio_builder')
            url = '/web?#id={id}&view_type=form&model={model}&action={action}'.format(
                id=r.id,
                model=r._name,
                action=action.id)
            r.act_window_url = url

    def action_view_formio(self):
        view_id = self.env.ref('formio.view_formio_builder_formio').id
        return {
            "name": self.name,
            "type": "ir.actions.act_window",
            "res_model": "formio.builder",
            "views": [(view_id, 'formio_builder')],
            "view_mode": "formio_builder",
            "target": "current",
            "res_id": self.id,
            "context": {}
        }

    def action_draft(self):
        self.write({'state': STATE_DRAFT})

    def action_current(self):
        self.ensure_one()
        self.write({'state': STATE_CURRENT})

    def action_obsolete(self):
        self.ensure_one()
        self.write({'state': STATE_OBSOLETE})

    @api.returns('self', lambda value: value)
    def copy_as_new_version(self):
        """Get last version for builder-forms by traversing-up on parent_id"""
        
        self.ensure_one()
        builder = self

        while builder.parent_id:
            builder = builder.parent_id
        builder = self.search([('name', '=', builder.name)], limit=1, order='id DESC')

        alter = {}
        alter["parent_id"] = self.id
        alter["state"] = STATE_DRAFT
        alter["version"] = builder.version + 1
        alter["version_comment"] = _('Write comment about version %s ...') % alter["version"]

        res = super(Builder, self).copy(alter)
        return res

    def action_new_builder_version(self):
        self.ensure_one()
        res = self.copy_as_new_version()

        form_view = self.env["ir.ui.view"].search(
            [("name", "=", "formio.builder.form")]
        )[0]

        tree_view = self.env["ir.ui.view"].search(
            [("name", "=", "formio.builder.tree")]
        )[0]

        return {
            "name": self.name,
            "type": "ir.actions.act_window",
            "res_model": "formio.builder",
            "view_type": "form",
            "view_mode": "form, tree",
            "views": [
                [form_view.id, "form"],
                [tree_view.id, "tree"],
            ],
            "target": "current",
            "res_id": res.id,
            "context": {}
        }

    def _get_js_options(self):
        """ formio JS (API) options """

        if self.formio_js_options:
            try:
                options = json.loads(self.formio_js_options)
            except:
                options = ast.literal_eval(self.formio_js_options)
        else:
            options = {}

        options['i18n'] = self.i18n_translations()

        # language
        Lang = self.env['res.lang']
        if self.env.user.lang in self.languages.mapped('code'):
            language = Lang._formio_ietf_code(self.env.user.lang)
        else:
            language = Lang._formio_ietf_code(self._context['lang'])

        # only set language if exist in i18n translations
        if options['i18n'].get(language):
            options['language'] = language
            
        return options

    def _get_js_params(self):
        """ Odoo JS (Owl component) misc. params """
        params = {}
        if self.state in [STATE_CURRENT, STATE_OBSOLETE]:
            params['readOnly'] = True
        return params

    def _get_public_form_js_params(self):
        """ Form: Odoo JS (Owl component) misc. params """
        params = {
            'public_submit_done_url': self.public_submit_done_url
        }
        return params

    @api.model
    def get_public_builder(self, uuid):
        """ Verifies public (e.g. website) access to forms and return builder or False. """

        domain = [
            ('uuid', '=', uuid),
            ('public', '=', True),
        ]
        builder = self.sudo().search(domain, limit=1)
        if builder:
            return builder
        else:
            return False

    @api.model
    def get_builder_by_name(self, name, state=STATE_CURRENT):
        """ Get the latest version of a builder by name. """

        domain = [
            ('name', '=', name),
            ('state', '=', state)
        ]
        builder = self.sudo().search(domain, limit=1)
        return builder or False

    def i18n_translations(self):
        i18n = {}
        # Formio GUI/API translations
        for trans in self.formio_version_id.translations:
            code = trans.lang_id.formio_ietf_code
            if trans.lang_id.code not in i18n:
                i18n[code] = {trans.property: trans.value}
            else:
                i18n[code][trans.property] = trans.value
        # Form Builder translations (labels etc).
        # These could override the former GUI/API translations, but
        # that's how the Javascript API works.
        for trans in self.translations:
            code = trans.lang_id.formio_ietf_code
            if trans.lang_id.code not in i18n:
                i18n[code] = {trans.source: trans.value}
            else:
                i18n[code][trans.source] = trans.value
        return i18n
