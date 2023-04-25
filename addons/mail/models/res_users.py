# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, exceptions, fields, models, modules, tools
from odoo.tools import email_normalize


class Users(models.Model):
    """ Update of res.users class
        - add a preference about sending emails about notifications
        - make a new user follow itself
        - add a welcome message
        - add suggestion preference
    """
    _name = 'res.users'
    _inherit = ['res.users']

    notification_type = fields.Selection([
        ('email', 'Handle by Emails'),
        ('inbox', 'Handle in Odoo')],
        'Notification', required=True, default='email',
        compute='_compute_notification_type', inverse='_inverse_notification_type', store=True,
        help="Policy on how to handle Chatter notifications:\n"
             "- Handle by Emails: notifications are sent to your email address\n"
             "- Handle in Odoo: notifications appear in your Odoo Inbox")
    res_users_settings_ids = fields.One2many('res.users.settings', 'user_id')
    # Provide a target for relateds that is not a x2Many field.
    res_users_settings_id = fields.Many2one('res.users.settings', string="Settings", compute='_compute_res_users_settings_id', search='_search_res_users_settings_id')

    _sql_constraints = [(
        "notification_type",
        "CHECK (notification_type = 'email' OR NOT share)",
        "Only internal user can receive notifications in Odoo",
    )]

    @api.depends('share', 'groups_id')
    def _compute_notification_type(self):
        # Because of the `groups_id` in the `api.depends`,
        # this code will be called for any change of group on a user,
        # even unrelated to the group_mail_notification_type_inbox or share flag.
        # e.g. if you add HR > Manager to a user, this method will be called.
        # It should therefore be written to be as performant as possible, and make the less change/write as possible
        # when it's not `mail.group_mail_notification_type_inbox` or `share` that are being changed.
        inbox_group_id = self.env['ir.model.data']._xmlid_to_res_id('mail.group_mail_notification_type_inbox')

        self.filtered_domain([
            ('groups_id', 'in', inbox_group_id), ('notification_type', '!=', 'inbox')
        ]).notification_type = 'inbox'
        self.filtered_domain([
            ('groups_id', 'not in', inbox_group_id), ('notification_type', '=', 'inbox')
        ]).notification_type = 'email'

        # Special case: internal users with inbox notifications converted to portal must be converted to email users
        self.filtered_domain([('share', '=', True), ('notification_type', '=', 'inbox')]).notification_type = 'email'

    def _inverse_notification_type(self):
        inbox_group = self.env.ref('mail.group_mail_notification_type_inbox')
        for user in self:
            if user.notification_type == 'inbox':
                user.groups_id += inbox_group
            else:
                user.groups_id -= inbox_group

    @api.depends('res_users_settings_ids')
    def _compute_res_users_settings_id(self):
        for user in self:
            user.res_users_settings_id = user.res_users_settings_ids and user.res_users_settings_ids[0]

    @api.model
    def _search_res_users_settings_id(self, operator, operand):
        return [('res_users_settings_ids', operator, operand)]

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['notification_type']

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ['notification_type']

    @api.model_create_multi
    def create(self, vals_list):

        users = super(Users, self).create(vals_list)

        # log a portal status change (manual tracking)
        log_portal_access = not self._context.get('mail_create_nolog') and not self._context.get('mail_notrack')
        if log_portal_access:
            for user in users:
                if user.has_group('base.group_portal'):
                    body = user._get_portal_access_update_body(True)
                    user.partner_id.message_post(
                        body=body,
                        message_type='notification',
                        subtype_xmlid='mail.mt_note'
                    )
        return users

    def write(self, vals):
        log_portal_access = 'groups_id' in vals and not self._context.get('mail_create_nolog') and not self._context.get('mail_notrack')
        user_portal_access_dict = {
            user.id: user.has_group('base.group_portal')
            for user in self
        } if log_portal_access else {}

        previous_email_by_user = {}
        if vals.get('email'):
            previous_email_by_user = {
                user: user.email
                for user in self.filtered(lambda user: bool(email_normalize(user.email)))
                if email_normalize(user.email) != email_normalize(vals['email'])
            }

        write_res = super(Users, self).write(vals)

        # log a portal status change (manual tracking)
        if log_portal_access:
            for user in self:
                user_has_group = user.has_group('base.group_portal')
                portal_access_changed = user_has_group != user_portal_access_dict[user.id]
                if portal_access_changed:
                    body = user._get_portal_access_update_body(user_has_group)
                    user.partner_id.message_post(
                        body=body,
                        message_type='notification',
                        subtype_xmlid='mail.mt_note'
                    )

        if 'login' in vals:
            self._notify_security_setting_update(
                _("Security Update: Login Changed"),
                _("Your account login has been updated"),
            )
        if 'password' in vals:
            self._notify_security_setting_update(
                _("Security Update: Password Changed"),
                _("Your account password has been updated"),
            )
        if 'email' in vals:
            # when the email is modified, we want notify the previous address (and not the new one)
            for user, previous_email in previous_email_by_user.items():
                self._notify_security_setting_update(
                    _("Security Update: Email Changed"),
                    _(
                        "Your account email has been changed from %(old_email)s to %(new_email)s.",
                        old_email=previous_email,
                        new_email=user.email,
                    ),
                    mail_values={'email_to': previous_email},
                    suggest_password_reset=False,
                )
        return write_res

    def _notify_security_setting_update(self, subject, content, mail_values=None, **kwargs):
        """ This method is meant to be called whenever a sensitive update is done on the user's account.
        It will send an email to the concerned user warning him about this change and making some security suggestions.

        :param str subject: The subject of the sent email (e.g: 'Security Update: Password Changed')
        :param str content: The text to embed within the email template (e.g: 'Your password has been changed')
        :param kwargs: 'suggest_password_reset' key:
            Whether or not to suggest the end-user to reset
            his password in the email sent.
            Defaults to True. """

        mail_create_values = []
        for user in self:
            body_html = self.env['ir.qweb']._render(
                'mail.account_security_setting_update',
                user._notify_security_setting_update_prepare_values(content, **kwargs),
                minimal_qcontext=True,
            )

            body_html = self.env['mail.render.mixin']._render_encapsulate(
                'mail.mail_notification_light',
                body_html,
                add_context={
                    # the 'mail_notification_light' expects a mail.message 'message' context, let's give it one
                    'message': self.env['mail.message'].sudo().new(dict(body=body_html, record_name=user.name)),
                    'model_description': _('Account'),
                    'company': user.company_id,
                },
            )

            vals = {
                'auto_delete': True,
                'body_html': body_html,
                'author_id': self.env.user.partner_id.id,
                'email_from': (
                    user.company_id.partner_id.email_formatted or
                    self.env.user.email_formatted or
                    self.env.ref('base.user_root').email_formatted
                ),
                'email_to': kwargs.get('force_email') or user.email_formatted,
                'subject': subject,
            }

            if mail_values:
                vals.update(mail_values)

            mail_create_values.append(vals)

        self.env['mail.mail'].sudo().create(mail_create_values)

    def _notify_security_setting_update_prepare_values(self, content, **kwargs):
        """" Prepare rendering values for the 'mail.account_security_setting_update' qweb template """

        reset_password_enabled = self.env['ir.config_parameter'].sudo().get_param("auth_signup.reset_password", True)
        return {
            'company': self.company_id,
            'password_reset_url': f"{self.get_base_url()}/web/reset_password",
            'security_update_text': content,
            'suggest_password_reset': kwargs.get('suggest_password_reset', True) and reset_password_enabled,
            'user': self,
            'update_datetime': fields.Datetime.now(),
        }

    def _get_portal_access_update_body(self, access_granted):
        body = _('Portal Access Granted') if access_granted else _('Portal Access Revoked')
        if self.partner_id.email:
            return '%s (%s)' % (body, self.partner_id.email)
        return body

    def _deactivate_portal_user(self, **post):
        """Blacklist the email of the user after deleting it.

        Log a note on the related partner so we know why it's archived.
        """
        current_user = self.env.user
        for user in self:
            user.partner_id._message_log(
                body=_('Archived because %(user_name)s (#%(user_id)s) deleted the portal account',
                       user_name=current_user.name, user_id=current_user.id)
            )

        if post.get('request_blacklist'):
            users_to_blacklist = [(user, user.email) for user in self.filtered(
                lambda user: tools.email_normalize(user.email))]
        else:
            users_to_blacklist = []

        super(Users, self)._deactivate_portal_user(**post)

        for user, user_email in users_to_blacklist:
            self.env['mail.blacklist']._add(
                user_email,
                message=_('Blocked by deletion of portal account %(portal_user_name)s by %(user_name)s (#%(user_id)s)',
                          user_name=current_user.name, user_id=current_user.id,
                          portal_user_name=user.name)
            )

    # ------------------------------------------------------------
    # DISCUSS
    # ------------------------------------------------------------

    def _init_messaging(self):
        self.ensure_one()
        odoobot = self.env.ref('base.partner_root')
        values = {
            'channels': self.partner_id._get_channels_as_member().channel_info(),
            'companyName': self.env.company.name,
            'currentGuest': False,
            'current_partner': self.partner_id.mail_partner_format().get(self.partner_id),
            'current_user_id': self.id,
            'current_user_settings': self.env['res.users.settings']._find_or_create_for_user(self)._res_users_settings_format(),
            'hasLinkPreviewFeature': self.env['mail.link.preview']._is_link_preview_enabled(),
            'internalUserGroupId': self.env.ref('base.group_user').id,
            'menu_id': self.env['ir.model.data']._xmlid_to_res_id('mail.menu_root_discuss'),
            'needaction_inbox_counter': self.partner_id._get_needaction_count(),
            'odoobot': odoobot.sudo().mail_partner_format().get(odoobot),
            'shortcodes': self.env['mail.shortcode'].sudo().search_read([], ['source', 'substitution']),
            'starred_counter': self.env['mail.message'].search_count([('starred_partner_ids', 'in', self.partner_id.ids)]),
        }
        return values

    @api.model
    def systray_get_activities(self):
        query = """SELECT m.id, count(*), act.res_model as model,
                        CASE
                            WHEN %(today)s::date - act.date_deadline::date = 0 Then 'today'
                            WHEN %(today)s::date - act.date_deadline::date > 0 Then 'overdue'
                            WHEN %(today)s::date - act.date_deadline::date < 0 Then 'planned'
                        END AS states
                    FROM mail_activity AS act
                    JOIN ir_model AS m ON act.res_model_id = m.id
                    WHERE user_id = %(user_id)s
                    GROUP BY m.id, states, act.res_model;
                    """
        self.env.cr.execute(query, {
            'today': fields.Date.context_today(self),
            'user_id': self.env.uid,
        })
        activity_data = self.env.cr.dictfetchall()
        model_ids = [a['id'] for a in activity_data]
        model_names = {n[0]: n[1] for n in self.env['ir.model'].sudo().browse(model_ids).name_get()}

        user_activities = {}
        for activity in activity_data:
            if not user_activities.get(activity['model']):
                module = self.env[activity['model']]._original_module
                icon = module and modules.module.get_module_icon(module)
                user_activities[activity['model']] = {
                    'id': activity['id'],
                    'name': model_names[activity['id']],
                    'model': activity['model'],
                    'type': 'activity',
                    'icon': icon,
                    'total_count': 0, 'today_count': 0, 'overdue_count': 0, 'planned_count': 0,
                }
            user_activities[activity['model']]['%s_count' % activity['states']] += activity['count']
            if activity['states'] in ('today', 'overdue'):
                user_activities[activity['model']]['total_count'] += activity['count']

            user_activities[activity['model']]['actions'] = [{
                'icon': 'fa-clock-o',
                'name': 'Summary',
            }]
        return list(user_activities.values())
