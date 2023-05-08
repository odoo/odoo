# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, exceptions, fields, models, modules, tools
from odoo.addons.base.models.res_users import is_selection_groups


class Users(models.Model):
    """ Update of res.users class
        - add a preference about sending emails about notifications
        - make a new user follow itself
        - add a welcome message
        - add suggestion preference
        - if adding groups to a user, check mail.channels linked to this user
          group, and the user. This is done by overriding the write method.
    """
    _name = 'res.users'
    _inherit = ['res.users']

    notification_type = fields.Selection([
        ('email', 'Handle by Emails'),
        ('inbox', 'Handle in Odoo')],
        'Notification', required=True, default='email',
        compute='_compute_notification_type', store=True, readonly=False,
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

    @api.depends('share')
    def _compute_notification_type(self):
        for user in self:
            # Only the internal users can receive notifications in Odoo
            if user.share or not user.notification_type:
                user.notification_type = 'email'

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
        # Auto-subscribe to channels unless skip explicitly requested
        if not self.env.context.get('mail_channel_nosubscribe'):
            self.env['mail.channel'].search([('group_ids', 'in', users.groups_id.ids)])._subscribe_users_automatically()
        return users

    def write(self, vals):
        log_portal_access = 'groups_id' in vals and not self._context.get('mail_create_nolog') and not self._context.get('mail_notrack')
        user_portal_access_dict = {
            user.id: user.has_group('base.group_portal')
            for user in self
        } if log_portal_access else {}

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

        if 'active' in vals and not vals['active']:
            self._unsubscribe_from_non_public_channels()
        sel_groups = [vals[k] for k in vals if is_selection_groups(k) and vals[k]]
        if vals.get('groups_id'):
            # form: {'group_ids': [(3, 10), (3, 3), (4, 10), (4, 3)]} or {'group_ids': [(6, 0, [ids]}
            user_group_ids = [command[1] for command in vals['groups_id'] if command[0] == 4]
            user_group_ids += [id for command in vals['groups_id'] if command[0] == 6 for id in command[2]]
            self.env['mail.channel'].search([('group_ids', 'in', user_group_ids)])._subscribe_users_automatically()
        elif sel_groups:
            self.env['mail.channel'].search([('group_ids', 'in', sel_groups)])._subscribe_users_automatically()
        return write_res

    def unlink(self):
        self._unsubscribe_from_non_public_channels()
        return super().unlink()

    def _unsubscribe_from_non_public_channels(self):
        """ This method un-subscribes users from group restricted channels. Main purpose
            of this method is to prevent sending internal communication to archived / deleted users.
            We do not un-subscribes users from public channels because in most common cases,
            public channels are mailing list (e-mail based) and so users should always receive
            updates from public channels until they manually un-subscribe themselves.
        """
        current_cm = self.env['mail.channel.member'].sudo().search([
            ('partner_id', 'in', self.partner_id.ids),
        ])
        current_cm.filtered(
            lambda cm: (cm.channel_id.channel_type == 'channel' and cm.channel_id.group_public_id)
        ).unlink()

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
            blacklist = self.env['mail.blacklist']._add(user_email)
            blacklist._message_log(
                body=_('Blocked by deletion of portal account %(portal_user_name)s by %(user_name)s (#%(user_id)s)',
                       user_name=current_user.name, user_id=current_user.id,
                       portal_user_name=user.name),
            )

    # ------------------------------------------------------------
    # DISCUSS
    # ------------------------------------------------------------

    def _init_messaging(self):
        self.ensure_one()
        partner_root = self.env.ref('base.partner_root')
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
            'partner_root': partner_root.sudo().mail_partner_format().get(partner_root),
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
