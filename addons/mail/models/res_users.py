# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
import contextlib

from odoo import _, api, Command, fields, models, modules, tools
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import email_normalize, str2bool
from odoo.addons.mail.tools.discuss import Store


class ResUsers(models.Model):
    """ Update of res.users class
        - add a preference about sending emails about notifications
        - make a new user follow itself
        - add a welcome message
        - add suggestion preference
    """
    _inherit = 'res.users'

    role_ids = fields.Many2many(
        "res.role",
        relation="res_role_res_users_rel",
        string="User Roles",
        help="Users are notified whenever one of their roles is @-mentioned in a conversation.",
    )
    can_edit_role = fields.Boolean(compute="_compute_can_edit_role")
    notification_type = fields.Selection([
        ('email', 'By Emails'),
        ('inbox', 'In Odoo')],
        'Notification', required=True, default='email',
        compute='_compute_notification_type', inverse='_inverse_notification_type', store=True,
        help="Policy on how to handle Chatter notifications:\n"
             "- By Emails: notifications are sent to your email address\n"
             "- In Odoo: notifications appear in your Odoo Inbox")
    presence_ids = fields.One2many("mail.presence", "user_id", groups="base.group_system")
    # OOO management
    out_of_office_from = fields.Datetime()
    out_of_office_to = fields.Datetime()
    out_of_office_message = fields.Html('Vacation Responder')
    is_out_of_office = fields.Boolean('Out of Office', compute='_compute_is_out_of_office')
    # sudo: res.users - can access presence of accessible user
    im_status = fields.Char("IM Status", compute="_compute_im_status", compute_sudo=True)
    manual_im_status = fields.Selection(
        [("away", "Away"), ("busy", "Do Not Disturb"), ("offline", "Offline")],
        string="IM status manually set by the user",
    )

    outgoing_mail_server_id = fields.Many2one(
        "ir.mail_server",
        "Outgoing Mail Server",
        compute='_compute_outgoing_mail_server_id',
        groups='base.group_user',
    )
    outgoing_mail_server_type = fields.Selection(
        [('default', 'Default')],
        "Outgoing Mail Server Type",
        compute='_compute_outgoing_mail_server_id',
        required=True,
        default='default',
        groups='base.group_user',
    )
    has_external_mail_server = fields.Boolean(compute='_compute_has_external_mail_server')

    def _compute_has_external_mail_server(self):
        self.has_external_mail_server = self.env['ir.config_parameter'].sudo().get_param(
            'base_setup.default_external_email_server')

    _notification_type = models.Constraint(
        "CHECK (notification_type = 'email' OR NOT share)",
        'Only internal user can receive notifications in Odoo',
    )

    @api.depends('share', 'all_group_ids')
    def _compute_notification_type(self):
        # Because of the `group_ids` in the `api.depends`,
        # this code will be called for any change of group on a user,
        # even unrelated to the group_mail_notification_type_inbox or share flag.
        # e.g. if you add HR > Manager to a user, this method will be called.
        # It should therefore be written to be as performant as possible, and make the less change/write as possible
        # when it's not `mail.group_mail_notification_type_inbox` or `share` that are being changed.
        inbox_group_id = self.env['ir.model.data']._xmlid_to_res_id('mail.group_mail_notification_type_inbox')

        self.filtered_domain([
            ('group_ids', 'in', inbox_group_id), ('notification_type', '!=', 'inbox')
        ]).notification_type = 'inbox'
        self.filtered_domain([
            ('group_ids', 'not in', inbox_group_id), ('notification_type', '=', 'inbox')
        ]).notification_type = 'email'

        # Special case: internal users with inbox notifications converted to portal must be converted to email users
        new_portal_users = self.filtered_domain([('share', '=', True), ('notification_type', '=', 'inbox')])
        new_portal_users.notification_type = 'email'
        new_portal_users.write({"group_ids": [Command.unlink(inbox_group_id)]})

    @api.depends('out_of_office_from', 'out_of_office_to')
    def _compute_is_out_of_office(self):
        """ Out-of-office is considered as activated once out_of_office_from is
        set in the past. "To" is not mandatory, as users could simply deactivate
        it when coming back if the leave timerange is unknown. """
        now = self.env.cr.now()
        todo = self.filtered(lambda u: u.out_of_office_from and u._is_internal())
        for user in todo:
            if user.out_of_office_to:
                user.is_out_of_office = (user.out_of_office_from <= now <= user.out_of_office_to)
            else:
                user.is_out_of_office = (user.out_of_office_from <= now)
        (self - todo).is_out_of_office = False

    @api.depends("manual_im_status", "presence_ids.status")
    def _compute_im_status(self):
        for user in self:
            user.im_status = (
                "offline"
                if user.presence_ids.status in ["offline", False]
                else user.manual_im_status or user.presence_ids.status
            )

    def _inverse_notification_type(self):
        inbox_group = self.env.ref('mail.group_mail_notification_type_inbox')
        inbox_users = self.filtered(lambda user: user.notification_type == 'inbox')
        inbox_users.write({"group_ids": [Command.link(inbox_group.id)]})
        (self - inbox_users).write({"group_ids": [Command.unlink(inbox_group.id)]})

    @api.depends_context("uid")
    def _compute_can_edit_role(self):
        self.can_edit_role = self.env["res.role"].sudo(False).has_access("write")

    @api.depends("email")
    def _compute_outgoing_mail_server_id(self):
        mail_servers = self.env['ir.mail_server'].sudo().search(fields.Domain.AND([
            [('from_filter', 'ilike', '_@_')],
            fields.Domain.OR([[
                ('from_filter', '=', user.email_normalized),
                ('smtp_user', '=', user.email),
                ('owner_user_id', '=', user._origin.id),
            ] for user in self]),
        ]))
        mail_servers = {m.owner_user_id: m for m in mail_servers}
        for user in self:
            server = mail_servers.get(user) or self.env['ir.mail_server']
            user.outgoing_mail_server_id = server.id
            type_options = self._fields['outgoing_mail_server_type']._selection
            user.outgoing_mail_server_type = (
                server.smtp_authentication
                if server.smtp_authentication in type_options
                else 'default'
            )

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            "can_edit_role",
            "is_out_of_office",
            "notification_type",
            "out_of_office_from",
            "out_of_office_message",
            "out_of_office_to",
            "role_ids",
            "has_external_mail_server",
            "outgoing_mail_server_id",
            "outgoing_mail_server_type",
        ]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + [
            "notification_type",
            "out_of_office_from",
            "out_of_office_message",
            "out_of_office_to",
        ]

    @api.model_create_multi
    def create(self, vals_list):

        users = super().create(vals_list)

        # log a portal status change (manual tracking)
        log_portal_access = not self.env.context.get('mail_create_nolog') and not self.env.context.get('mail_notrack')
        if log_portal_access:
            for user in users:
                if user._is_portal():
                    body = user._get_portal_access_update_body(True)
                    user.partner_id.message_post(
                        body=body,
                        message_type='notification',
                        subtype_xmlid='mail.mt_note'
                    )
        return users

    def write(self, vals):
        log_portal_access = 'group_ids' in vals and not self.env.context.get('mail_create_nolog') and not self.env.context.get('mail_notrack')
        user_portal_access_dict = {
            user.id: user._is_portal()
            for user in self
        } if log_portal_access else {}

        previous_email_by_user = {}
        if vals.get('email'):
            previous_email_by_user = {
                user: user.email
                for user in self.filtered(lambda user: bool(user.email_normalized))
                if user.email_normalized != email_normalize(vals['email'])
            }
        if 'notification_type' in vals:
            user_notification_type_modified = self.filtered(lambda user: user.notification_type != vals['notification_type'])

        write_res = super().write(vals)

        # log a portal status change (manual tracking)
        if log_portal_access:
            for user in self:
                user_has_group = user._is_portal()
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
        if "notification_type" in vals:
            for user in user_notification_type_modified:
                Store(bus_channel=user).add(user, "notification_type").bus_send()

        return write_res

    def action_archive(self):
        activities_to_delete = self.env['mail.activity'].sudo().search([('user_id', 'in', self.ids)])
        activities_to_delete.unlink()
        return super().action_archive()

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
            body_html = self.env['mail.render.mixin']._render_template(
                'mail.account_security_alert',
                model='res.users',
                res_ids=user.ids,
                engine='qweb_view',
                options={'post_process': True},
                add_context=user._notify_security_setting_update_prepare_values(content, **kwargs),
            )[user.id]

            body_html = self.env['mail.render.mixin']._render_encapsulate(
                'mail.mail_notification_light',
                body_html,
                add_context={
                    'model_description': _('Account'),
                },
                context_record=user,
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

        mails = self.env['mail.mail'].sudo().create(mail_create_values)
        with contextlib.suppress(Exception):
            mails.send()
        return mails

    def _notify_security_setting_update_prepare_values(self, content, **kwargs):
        """"Prepare rendering values for the 'mail.account_security_alert' qweb template."""
        reset_password_enabled = str2bool(self.env['ir.config_parameter'].sudo().get_param("auth_signup.reset_password", True))

        values = {
            'browser': False,
            'content': content,
            'event_datetime': fields.Datetime.now(),
            'ip_address': False,
            'location_address': False,
            'suggest_password_reset': kwargs.get('suggest_password_reset', True) and reset_password_enabled,
            'user': self,
            'useros': False,
        }
        if not request:
            return values

        city = request.geoip.get('city') or False
        region = request.geoip.get('region_name') or False
        country = request.geoip.get('country') or False
        if country:
            if region and city:
                values['location_address'] = _("Near %(city)s, %(region)s, %(country)s", city=city, region=region, country=country)
            elif region:
                values['location_address'] = _("Near %(region)s, %(country)s", region=region, country=country)
            else:
                values['location_address'] = _("In %(country)s", country=country)
        values['ip_address'] = request.httprequest.environ['REMOTE_ADDR']
        if request.httprequest.user_agent:
            if request.httprequest.user_agent.browser:
                values['browser'] = request.httprequest.user_agent.browser.capitalize()
            if request.httprequest.user_agent.platform:
                values['useros'] = request.httprequest.user_agent.platform.capitalize()
        return values

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

        super()._deactivate_portal_user(**post)

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

    @api.model
    def _init_store_data(self, store: Store):
        """Initialize the store of the user."""
        xmlid_to_res_id = self.env["ir.model.data"]._xmlid_to_res_id
        # sudo: res.partner - exposing OdooBot data is considered acceptable
        odoobot = self.env.ref("base.partner_root").sudo()
        if not self.env.user._is_public():
            odoobot = odoobot.with_prefetch((odoobot + self.env.user.partner_id).ids)
        store.add_global_values(
            action_discuss_id=xmlid_to_res_id("mail.action_discuss"),
            hasLinkPreviewFeature=self.env["mail.link.preview"]._is_link_preview_enabled(),
            internalUserGroupId=self.env.ref("base.group_user").id,
            mt_comment=xmlid_to_res_id("mail.mt_comment"),
            mt_note=xmlid_to_res_id("mail.mt_note"),
            odoobot=Store.One(odoobot),
        )
        if not self.env.user._is_public():
            settings = self.env["res.users.settings"]._find_or_create_for_user(self.env.user)
            store.add_global_values(
                self_partner=Store.One(
                    self.env.user.partner_id,
                    [
                        "active",
                        "avatar_128",
                        "im_status",
                        Store.One(
                            "main_user_id",
                            [
                                Store.Attr("is_admin", lambda u: u._is_admin()),
                                "notification_type",
                                "share",
                                "signature",
                            ],
                        ),
                        "name",
                    ],
                ),
                settings=settings._res_users_settings_format(),
            )
        if guest := self.env["mail.guest"]._get_guest_from_context():
            # sudo() => adding current guest data is acceptable
            store.add_global_values(self_guest=Store.One(guest.sudo(), ["avatar_128", "name"]))

    def _init_messaging(self, store: Store):
        self.ensure_one()
        self = self.with_user(self)
        # sudo: bus.bus: reading non-sensitive last id
        bus_last_id = self.env["bus.bus"].sudo()._bus_last_id()
        store.add_global_values(
            inbox={
                "counter": self.partner_id._get_needaction_count(),
                "counter_bus_id": bus_last_id,
                "id": "inbox",
                "model": "mail.box",
            },
            starred={
                "counter": self.env["mail.message"].search_count(
                    [("starred_partner_ids", "in", self.partner_id.ids)]
                ),
                "counter_bus_id": bus_last_id,
                "id": "starred",
                "model": "mail.box",
            },
        )

    @api.model
    def _get_activity_groups(self):
        search_limit = int(self.env['ir.config_parameter'].sudo().get_param('mail.activity.systray.limit', 1000))
        activities = self.env["mail.activity"].search(
            [("user_id", "=", self.env.uid)],
            order='id desc', limit=search_limit,
        )

        user_company_ids = self.env.user.company_ids.ids
        is_all_user_companies_allowed = set(user_company_ids) == set(self.env.context.get('allowed_company_ids') or [])

        activities_model_groups = defaultdict(lambda: self.env["mail.activity"])
        activities_rec_groups = defaultdict(lambda: defaultdict(lambda: self.env["mail.activity"]))

        for activity in activities:
            if activity.res_model:
                activities_rec_groups[activity.res_model][activity.res_id] += activity
            else:
                activities_rec_groups["mail.activity"][False] += activity
        model_activity_states = {
            'mail.activity': {'overdue_count': 0, 'today_count': 0, 'planned_count': 0, 'total_count': 0}
        }
        for model_name, activities_by_record in activities_rec_groups.items():
            res_ids = activities_by_record.keys()
            Model = self.env[model_name]
            has_model_access_right = Model.has_access('read')
            if has_model_access_right:
                allowed_records = Model.browse(res_ids)._filtered_access('read')
            else:
                allowed_records = Model
            unallowed_records = Model.browse(res_ids) - allowed_records
            # We remove from not allowed records, records that the user has access to through others of his companies
            if has_model_access_right and unallowed_records and not is_all_user_companies_allowed:
                unallowed_records -= unallowed_records.with_context(
                    allowed_company_ids=user_company_ids)._filtered_access('read')
            model_activity_states[model_name] = {'overdue_count': 0, 'today_count': 0, 'planned_count': 0, 'total_count': 0}
            for record_id, activities in activities_by_record.items():
                if record_id in unallowed_records.ids or not record_id:
                    model_key = 'mail.activity'
                    activities_model_groups['mail.activity'] += activities
                elif record_id in allowed_records.ids:
                    model_key = model_name
                    activities_model_groups[model_name] += activities
                elif record_id:
                    continue

                # counter: record-based activities count as 1 (record is main)
                # but free activities count as 'number of activities', each one
                # is individual
                count = 1 if (record_id and record_id in allowed_records.ids) else len(activities)
                # update counters; note that "total" is actually the "todo" total
                # not containing planned
                if 'overdue' in activities.mapped('state'):
                    model_activity_states[model_key]['overdue_count'] += count
                    model_activity_states[model_key]['total_count'] += count
                elif 'today' in activities.mapped('state'):
                    model_activity_states[model_key]['today_count'] += count
                    model_activity_states[model_key]['total_count'] += count
                else:
                    model_activity_states[model_key]['planned_count'] += count

        model_ids = [self.env["ir.model"]._get_id(name) for name in activities_model_groups]
        user_activities = {}
        for model_name, activities in activities_model_groups.items():
            Model = self.env[model_name]
            module = Model._original_module
            icon = module and modules.module.get_module_icon(module)
            model = self.env["ir.model"]._get(model_name).with_prefetch(model_ids)
            user_activities[model_name] = {
                "id": model.id,
                "name": model.name if model_name != "mail.activity" else _("Other activities"),
                "model": model_name,
                "type": "activity",
                "icon": icon,
                # activity more important than archived status, active_test is too broad
                "domain": [('active', 'in', [True, False])] if model_name != "mail.activity" and "active" in Model else [],
                "total_count": model_activity_states[model_name]['total_count'],
                "today_count": model_activity_states[model_name]['today_count'],
                "overdue_count": model_activity_states[model_name]['overdue_count'],
                "planned_count": model_activity_states[model_name]['planned_count'],
                "view_type": getattr(Model, '_systray_view', 'list'),
            }
            if model_name == 'mail.activity':
                user_activities[model_name]['activity_ids'] = activities.ids
        return list(user_activities.values())

    def _get_store_avatar_card_fields(self, target):
        return ["share", Store.One("partner_id", self.partner_id._get_store_avatar_card_fields(target))]

    # ------------------------------------------------------------
    # Mail Servers
    # ------------------------------------------------------------

    @api.autovacuum
    def _gc_personal_mail_servers(self):
        """In case the user change their email, we need to delete the old personal servers."""
        self.env['ir.mail_server'].with_context(active_test=False) \
            .search([('owner_user_id', '!=', False)]) \
            .filtered(lambda s: s.owner_user_id.outgoing_mail_server_id != s or not s.active) \
            .unlink()

    @api.model
    def _get_mail_server_values(self, server_type):
        return {}

    @api.model
    def action_setup_outgoing_mail_server(self, server_type):
        """Configure the outgoing mail servers."""
        user = self.env.user
        if not user.has_external_mail_server:
            raise UserError(_('You are not allowed to create a personal mail server.'))

        if not user._is_internal():
            raise UserError(_('Only internal users can configure a personal mail server.'))

        existing_mail_server = self.env["ir.mail_server"].sudo() \
            .with_context(active_test=False).search([("owner_user_id", "=", user.id)])

        if server_type == 'default':
            # Use the default server
            if existing_mail_server:
                existing_mail_server.unlink()

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "message": _("Switching back to the default server."),
                    "type": "warning",
                },
            }

        email = user.email
        if not email:
            raise UserError(_("Please set your email before connecting your mail server."))

        normalized_email = tools.email_normalize(email)
        if (
            not normalized_email
            or "@" not in normalized_email
            # Be sure it's well parsed by `ir.mail_server`
            or self.env["ir.mail_server"]._parse_from_filter(normalized_email)
            != [normalized_email]
        ):
            raise UserError(_("Wrong email address %s.", email))

        # Check that the user's email is not used by `mail.alias.domain` to avoid leaking the outgoing emails
        alias_domain = self.env["mail.alias.domain"].sudo().search([])
        cli_default_from = tools.config.get("email_from")
        match_from_filter = self.env["ir.mail_server"]._match_from_filter
        if (
            any(match_from_filter(e, normalized_email) for e in alias_domain.mapped("default_from_email"))
            or (cli_default_from and match_from_filter(cli_default_from, normalized_email))
        ):
            raise UserError(_("Your email address is used by an alias domain, and so you can not create a mail server for it."))

        if (
            server_type == user.outgoing_mail_server_type
            and user.outgoing_mail_server_id.from_filter == normalized_email
            and user.outgoing_mail_server_id.smtp_user == normalized_email
        ):
            # Re-connect the account
            return self._get_mail_server_setup_end_action(user.outgoing_mail_server_id)

        if existing_mail_server:
            existing_mail_server.unlink()

        values = {
            # Will be un-archived once logged in
            # Archived personal server will be deleted in GC CRON
            # to clean pending connection that didn't finish
            "active": False,
            "name": _("%s's outgoing email", user.name),
            "smtp_user": normalized_email,
            "smtp_pass": False,
            "from_filter": normalized_email,
            "smtp_port": 587,
            "smtp_encryption": "starttls",
            "owner_user_id": user.id,
            **self._get_mail_server_values(server_type),
        }
        smtp_server = self.env["ir.mail_server"].sudo().create(values)
        return self._get_mail_server_setup_end_action(smtp_server)

    @api.model
    def action_test_outgoing_mail_server(self):
        user = self.env.user
        if not user.has_external_mail_server:
            raise UserError(_('You are not allowed to test personal mail servers.'))

        if not user.has_group('base.group_user'):
            raise UserError(_('Only internal users can configure personal mail servers.'))

        server_sudo = user.outgoing_mail_server_id.sudo()
        if not server_sudo:
            raise UserError(_('No mail server configured'))
        server_sudo.test_smtp_connection()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Connection Test Successful!'),
                'type': 'success',
            },
        }

    @api.model
    def _get_mail_server_setup_end_action(self, smtp_server):
        raise NotImplementedError()
