# Copyright Nova Code (http://www.novacode.nl)
# See LICENSE file for full licensing details.

import ast
import json
import re
import uuid

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError

from ..utils import get_field_selection_label

from .formio_builder import STATE_CURRENT as BUILDER_STATE_CURRENT

STATE_PENDING = 'PENDING'
STATE_DRAFT = 'DRAFT'
STATE_COMPLETE = 'COMPLETE'
STATE_CANCEL = 'CANCEL'


class Form(models.Model):
    _name = 'formio.form'
    _description = 'Form'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    _order = 'id DESC'

    _interval_selection = {'minutes': 'Minutes', 'hours': 'Hours', 'days': 'Days'}
    _interval_types = {
        'minutes': lambda interval: relativedelta(minutes=interval),
        'hours': lambda interval: relativedelta(hours=interval),
        'days': lambda interval: relativedelta(days=interval),
    }

    builder_id = fields.Many2one(
        'formio.builder', string='Form builder', required=True,
        ondelete='restrict', domain=[('state', '=', BUILDER_STATE_CURRENT)])
    name = fields.Char(related='builder_id.name', readonly=True)
    uuid = fields.Char(
        default=lambda self: self._default_uuid(), required=True, readonly=True, copy=False,
        string='UUID')
    title = fields.Char(string='Title', required=True, index=True, tracking=True)
    state = fields.Selection(
        [(STATE_PENDING, 'Pending'), (STATE_DRAFT, 'Draft'),
         (STATE_COMPLETE, 'Completed'), (STATE_CANCEL, 'Canceled')],
        string="State", default=STATE_PENDING, tracking=True, index=True)
    display_state = fields.Char("Display State", compute='_compute_display_fields', store=False)
    kanban_group_state = fields.Selection(
        [('A', 'Pending'), ('B', 'Draft'), ('C', 'Completed'), ('D', 'Canceled')],
        compute='_compute_kanban_group_state', store=True)
    url = fields.Char(compute='_compute_url', readonly=True)
    act_window_url = fields.Char(compute='_compute_act_window_url', readonly=True)
    act_window_multi_url = fields.Char(compute='_compute_act_window_url', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner', tracking=True)
    initial_res_model_id = fields.Many2one(related='builder_id.res_model_id', readonly=True, string='Resource Model #1')
    initial_res_model_name = fields.Char(related='initial_res_model_id.name', readonly=True, string='Resource Name #1')
    initial_res_model = fields.Char(related='initial_res_model_id.model', readonly=True, string='Resource Model Name #1')
    initial_res_id = fields.Integer("Record ID #1", help="Database ID of the record in res_model to which this applies")
    res_model_id = fields.Many2one('ir.model', readonly=True, string='Resource Model')
    res_model_name = fields.Char(related='res_model_id.name', readonly=True, string='Resource Name')
    res_model = fields.Char(related='res_model_id.model', readonly=True, string='Resource Model Name')
    res_id = fields.Integer("Record ID", help="Database ID of the record in res_model to which this applies")
    res_act_window_url = fields.Char(readonly=True)
    res_name = fields.Char(string='Record  Name', readonly=True)
    res_partner_id = fields.Many2one('res.partner', readonly=True, string='Resource Partner')
    user_id = fields.Many2one(
        'res.users', string='Assigned user',
        index=True, tracking=True)
    assigned_partner_id = fields.Many2one('res.partner', related='user_id.partner_id', string='Assigned Partner')
    assigned_partner_name = fields.Char(related='assigned_partner_id.name', string='Assigned Partner Name')
    invitation_mail_template_id = fields.Many2one(
        'mail.template', 'Invitation Mail',
        domain=[('model', '=', 'formio.form')],
        help="This e-mail template will be sent on user assignment. Leave empty to send nothing.")
    submission_data = fields.Text('Data', default=False)
    submission_user_id = fields.Many2one(
        'res.users', string='Submission User', readonly=True,
        help='User who submitted the form.')
    submission_partner_id = fields.Many2one('res.partner', related='submission_user_id.partner_id', string='Submission Partner')
    submission_partner_name = fields.Char(related='submission_partner_id.name', string='Submission Partner Name')
    submission_date = fields.Datetime(
        string='Submission Date', readonly=True, tracking=True,
        help='Datetime when the form was last submitted.')
    sequence = fields.Integer(help="Usefull when storing and listing forms in an ordered way")
    portal = fields.Boolean("Portal (Builder)", related='builder_id.portal', readonly=True, help="Form is accessible by assigned portal user")
    portal_share = fields.Boolean("Portal")
    portal_submit_done_url = fields.Char(related='builder_id.portal_submit_done_url')
    public = fields.Boolean("Public (Builder)", related='builder_id.public', readonly=True)
    public_share = fields.Boolean("Public", tracking=True, help="Share form in public? (with access expiration check).")
    public_access_date_from = fields.Datetime(
        string='Public Access From', tracking=True, help='Datetime from when the form is public shared until it expires.')
    public_access_interval_number = fields.Integer(tracking=True)
    public_access_interval_type = fields.Selection(list(_interval_selection.items()), tracking=True)
    public_access = fields.Boolean("Public Access", compute='_compute_access', help="The Public Access check. Computed public access by checking whether (field) Public Access From has been expired.")
    public_create = fields.Boolean("Public Created", readonly=True, help="Form was public created")
    show_title = fields.Boolean("Show Title")
    show_state = fields.Boolean("Show State")
    show_id = fields.Boolean("Show ID")
    show_uuid = fields.Boolean("Show UUID")
    show_user_metadata = fields.Boolean("Show User Metadata")
    languages = fields.One2many('res.lang', related='builder_id.languages', string='Languages')
    allow_unlink = fields.Boolean("Allow delete", compute='_compute_access')
    allow_force_update_state = fields.Boolean("Allow force update State", compute='_compute_access')
    readonly_submission_data = fields.Boolean("Data is readonly", compute='_compute_access')
    allow_copy = fields.Boolean(string='Allow Copies', help='Allow copying form submissions.', tracking=True, default=True)
    copy_to_current = fields.Boolean(string='Copy To Current', help='When copying a form, always link it to the current version of the builder instead of the original builder.', tracking=True, default=True)

    @api.model
    def default_get(self, fields):
        result = super(Form, self).default_get(fields)
        # XXX Override (ORM) default value 0 (zero) for Integer field.
        result['res_id'] = False
        return result

    @api.model
    def create(self, vals):
        vals = self._prepare_create_vals(vals)
        res = super(Form, self).create(vals)
        res._after_create(vals)
        return res

    def write(self, vals):
        res = super(Form, self).write(vals)
        self._after_write(vals)
        return res

    def _prepare_create_vals(self, vals):
        builder = self._get_builder_from_id(vals.get('builder_id'))

        vals['show_title'] = builder.show_form_title
        vals['show_state'] = builder.show_form_state
        vals['show_id'] = builder.show_form_id
        vals['show_uuid'] = builder.show_form_uuid
        vals['show_user_metadata'] = builder.show_form_user_metadata
        vals['allow_copy'] = builder.form_allow_copy
        vals['copy_to_current'] = builder.form_copy_to_current

        # access
        vals['portal_share'] = builder.portal
        if builder.public or self.env.user.id == self.env.ref('base.public_user').id:
            vals['public_access'] = True
            vals['public_access_date_from'] = fields.Datetime.now()

        # public_share exiration fields (store always)
        vals['public_access_interval_number'] = builder.public_access_interval_number
        vals['public_access_interval_type'] = builder.public_access_interval_type

        # resource model, id
        vals['res_model_id'] = builder.res_model_id.id

        if not vals.get('res_id'):
            vals['res_id'] = self._context.get('active_id')

        vals['initial_res_id'] = vals['res_id']

        if not vals.get('res_name'):
            vals['res_name'] = builder.res_model_id.name
        return vals

    def _after_create(self, vals):
        self._process_api_components(vals)

    def _after_write(self, vals):
        self._process_api_components(vals)

    def _process_api_components(self, vals):
        if vals.get('submission_data') and self.builder_id.component_partner_email:
            submission_data = self._decode_data(vals['submission_data'])

            if submission_data.get(self.builder_id.component_partner_email):
                partner_email = submission_data.get(self.builder_id.component_partner_email)
                partner_model = self.env['res.partner']
                partner = partner_model.search([('email', '=', partner_email)])

                if not partner:
                    # Only create partner, don't update fields if exist already!
                    default_partner_vals = {'email': partner_email}
                    partner_vals = self._prepare_partner_vals(submission_data, default_partner_vals)
                    partner = partner_model.create(partner_vals)
                if len(partner) == 1:
                    self.write({'partner_id': partner.id})
                    if self.builder_id.component_partner_add_follower:
                        self.message_subscribe(partner_ids=partner.ids)
                elif len(partner) > 1:
                    self.mail_activity_partner_linking(partner_email, record=self)

    def _prepare_partner_vals(self, submission_data, partner_vals):
        if submission_data.get(self.builder_id.component_partner_name):
            partner_vals['name'] = submission_data.get(self.builder_id.component_partner_name)
        return partner_vals

    def _get_builder_from_id(self, builder_id):
        return self.env['formio.builder'].browse(builder_id)

    @api.depends('state')
    def _compute_kanban_group_state(self):
        for r in self:
            if r.state == STATE_PENDING:
                r.kanban_group_state = 'A'
            if r.state == STATE_DRAFT:
                r.kanban_group_state = 'B'
            if r.state == STATE_COMPLETE:
                r.kanban_group_state = 'C'
            if r.state == STATE_CANCEL:
                r.kanban_group_state = 'D'

    def _compute_access(self):
        user_groups = self.env.user.groups_id
        for form in self:
            # allow_unlink
            unlink_form = self.get_form(form.uuid, 'unlink')
            if unlink_form:
                form.allow_unlink = True
            else:
                form.allow_unlink = False

            # allow_state_update
            if self.env.user.has_group('formio.group_formio_admin'):
                form.allow_force_update_state = True
            elif form.builder_id.allow_force_update_state_group_ids and \
                 (user_groups & form.builder_id.allow_force_update_state_group_ids):
                form.allow_force_update_state = True
            else:
                form.allow_force_update_state = False

            # readonly_submission_data
            if self.env.user.has_group('formio.group_formio_admin'):
                form.readonly_submission_data = False
            else:
                form.readonly_submission_data = True

            # public
            form.public_access = form._public_access()
            
    def _public_access(self):
        if self.public_share and self.public_access_date_from:
            now = fields.Datetime.now()
            expire_on = self.public_access_date_from + self._interval_types[self.public_access_interval_type](self.public_access_interval_number)
            
            if self.public_access_interval_number == 0:
                return False
            elif self.public_access_date_from > now:
                return False
            else:
                return expire_on >= now
        else:
            return False

    @api.depends('state')
    def _compute_display_fields(self):
        for r in self:
            r.display_state = get_field_selection_label(r, 'state')

    @api.depends('title')
    def name_get(self):
        res = []
        for r in self:
            name = '{title} [{id}]'.format(
                title=r.title, id=r.id
            )
            res.append((r.id, name))
        return res

    def _decode_data(self, data):
        """ Convert data (str) to dictionary

        json.loads(data) refuses identifies with single quotes.Use
        ast.literal_eval() instead.

        :param str data: submission_data string
        :return str data: submission_data as dictionary
        """
        try:
            data = json.loads(data)
        except:
            data = ast.literal_eval(data)
        return data

    def action_view_formio(self):
        return {
            "name": self.name,
            "type": "ir.actions.act_window",
            "res_model": "formio.form",
            "views": [(False, 'formio_form')],
            "view_mode": "formio_form",
            "target": "current",
            "res_id": self.id,
            "context": {}
        }

    def action_draft(self):
        if not self.allow_force_update_state:
            raise UserError(_("You're not allowed to (force) update the Form into Draft state."))

        vals = {'state': STATE_DRAFT}
        submission_data = self._decode_data(self.submission_data)
        if 'submit' in submission_data:
            del submission_data['submit']
            vals['submission_data'] = json.dumps(submission_data)

        self.with_context(formio_form_action_draft=True).write(vals)

    def action_complete(self):
        if not self.allow_force_update_state:
            raise UserError(_("You're not allowed to (force) update the Form into Complete state."))
        self.write({'state': STATE_COMPLETE})

    def action_cancel(self):
        if not self.allow_force_update_state:
            raise UserError(_("You're not allowed to (force) update the Form into Cancel state."))
        self.write({'state': STATE_CANCEL})

    def action_copy(self, force_copy_to_current=False):
        if not self.allow_copy:
            raise UserError(_("You're not allowed to copy this form."))

        builder = self.builder_id
        if self.copy_to_current or force_copy_to_current:
            builder = self.env['formio.builder'].get_builder_by_name(self.builder_id.name)

        if not builder:
            raise UserError(_("There is no Form Builder available to link this form to."))

        return self.copy(default={'state': STATE_DRAFT, 'builder_id': builder.id})

    def action_copy_to_current(self):
        new_form = self.action_copy(force_copy_to_current=True)

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'formio.form',
            'target': 'current',
            'res_id': new_form.id,
        }

    def action_send_invitation_mail(self):
        compose_form_id = self.env.ref('mail.email_compose_message_wizard_form').id
        if self.portal:
            template_id = self.env.ref('formio.mail_invitation_portal_user').id
        else:
            template_id = self.env.ref('formio.mail_invitation_internal_user').id
        ctx = dict(
            default_composition_mode='comment',
            default_res_id=self.id,
            default_model='formio.form',
            default_use_template=bool(template_id),
            default_template_id=template_id,
            custom_layout='mail.mail_notification_light'
        )
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    @api.model
    def _default_uuid(self):
        return str(uuid.uuid4())

    @api.onchange('builder_id')
    def _onchange_builder_domain(self):
        domain = [
            ('state', '=', BUILDER_STATE_CURRENT),
            ('res_model_id', '=', False),
        ]
        res = {
            'domain': {'builder_id': domain}
        }
        return res

    @api.onchange('builder_id')
    def _onchange_builder(self):
        if not self.env.user.has_group('formio.group_formio_user_all_forms'):
            self.user_id = self.env.user.id
        self.title = self.builder_id.title
        self.show_title = self.builder_id.show_form_title
        self.show_state = self.builder_id.show_form_state
        self.show_id = self.builder_id.show_form_id
        self.show_uuid = self.builder_id.show_form_uuid
        self.show_user_metadata = self.builder_id.show_form_user_metadata

        # public share
        self.public_share = self.builder_id.public
        self.public_access_interval_number = self.builder_id.public_access_interval_number
        self.public_access_interval_type = self.builder_id.public_access_interval_type
        
        if self.builder_id.public:
            self.public_access_date_from = fields.Datetime.now()

    @api.onchange('portal')
    def _onchange_portal(self):
        res = {}
        group_portal = self.env.ref('base.group_portal').id
        group_formio_user = self.env.ref('formio.group_formio_user').id
        group_formio_user_all = self.env.ref('formio.group_formio_user_all_forms').id
        if not self.portal:
            if self.user_id.has_group('base.group_portal'):
                self.user_id = False
            res['domain'] = {
                'user_id': [
                    ('groups_id', '!=', group_portal),
                    '|',
                    ('groups_id', '=', group_formio_user),
                    ('groups_id', '=', group_formio_user_all),
                ]}
        else:
            res['domain'] = {
                'user_id': [
                    '|',
                    ('groups_id', '=', group_portal),
                    ('groups_id', '!=', False)
                ]
            }
        return res

    def _compute_url(self):
        # sudo() is needed for regular users.
        for r in self:
            url = '{base_url}/formio/form/{uuid}'.format(
                base_url=r.env['ir.config_parameter'].sudo().get_param('web.base.url'),
                uuid=r.uuid)
            r.url = url

    def _compute_act_window_url(self):
        # sudo() is needed for regular users.
        for r in self:
            action = self.env.ref('formio.action_formio_form')
            url = '/web?#id={id}&view_type=form&model={model}&action={action}'.format(
                id=r.id,
                model=r._name,
                action=action.id)
            r.act_window_url = url

    def action_open_res_act_window(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.res_model,
            'res_id': self.res_id,
            "views": [[False, "form"]],
        }

    @api.model
    def get_form(self, uuid, mode):
        """ Verifies access to form and return form or False. """

        if not self.env['formio.form'].check_access_rights(mode, False):
            return False

        # check access rules
        form = self.sudo().search([('uuid', '=', uuid)], limit=1)
        if form:
            try:
                # Catch the deny access exception
                form.check_access_rule(mode)
            except AccessError as e:
                return False

        # portal user
        if self.env.user.has_group('base.group_portal'):
            form = self.sudo().search([('uuid', '=', uuid)], limit=1)
            if not form or not form.portal_share or form.user_id.id != self.env.user.id:
                return False
        return form

    @api.model
    def get_public_form(self, uuid, public_share=False):
        """ Check access and return public form or False. """

        domain = [
            ('uuid', '=', uuid),
            ('public_share', '=', public_share)
        ]
        form = self.sudo().search(domain, limit=1)
        if form and form.public_access:
            return form
        else:
            return False

    def _get_js_options(self):
        """ formio JS (API) options """
        options = {
            'i18n': self.i18n_translations()
        }
        if self.state in [STATE_COMPLETE, STATE_CANCEL]:
            options['readOnly'] = True

            if self.builder_id.view_as_html:
                options['renderMode'] = 'html'
                options['viewAsHtml'] = True # backwards compatible (version < 4.x)?
        return options

    def _get_js_params(self):
        """ Odoo JS (Owl component) misc. params """
        params = {
            'portal_submit_done_url': self.portal_submit_done_url
        }
        return params

    def _etl_odoo_data(self):
        return {}

    def i18n_translations(self):
        i18n = self.builder_id.i18n_translations()
        return i18n

    def mail_activity_partner_linking(self, partner_email, record=False, user_id=False):
        if not user_id:
            user_id = self.builder_id.component_partner_activity_user_id
        if user_id:
            rec = record or self
            rec.activity_schedule(
                'formio.mail_act_partner_linking',
                user_id=user_id.id,
                summary=_('Link the Form to the appropriate Partner'),
                note=_('Found multiple Partners with email <strong>%s</strong> submitted in the Form.') % partner_email
            )
        else:
            _logger.error('No user configured (in settings) for mail_activity_partner_linking')
