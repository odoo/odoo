# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import _, api, exceptions, fields, models, modules
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
    _description = 'Users'

    notification_type = fields.Selection([
        ('email', 'Handle by Emails'),
        ('inbox', 'Handle in Odoo')],
        'Notification', required=True, default='email',
        help="Policy on how to handle Chatter notifications:\n"
             "- Handle by Emails: notifications are sent to your email address\n"
             "- Handle in Odoo: notifications appear in your Odoo Inbox")
    # channel-specific: moderation
    is_moderator = fields.Boolean(string='Is moderator', compute='_compute_is_moderator')
    moderation_counter = fields.Integer(string='Moderation count', compute='_compute_moderation_counter')
    moderation_channel_ids = fields.Many2many(
        'mail.channel', 'mail_channel_moderator_rel',
        string='Moderated channels')

    @api.depends('moderation_channel_ids.moderation', 'moderation_channel_ids.moderator_ids')
    def _compute_is_moderator(self):
        moderated = self.env['mail.channel'].search([
            ('id', 'in', self.mapped('moderation_channel_ids').ids),
            ('moderation', '=', True),
            ('moderator_ids', 'in', self.ids)
        ])
        user_ids = moderated.mapped('moderator_ids')
        for user in self:
            user.is_moderator = user in user_ids

    def _compute_moderation_counter(self):
        self._cr.execute("""
SELECT channel_moderator.res_users_id, COUNT(msg.id)
FROM "mail_channel_moderator_rel" AS channel_moderator
JOIN "mail_message" AS msg
ON channel_moderator.mail_channel_id = msg.res_id
    AND channel_moderator.res_users_id IN %s
    AND msg.model = 'mail.channel'
    AND msg.moderation_status = 'pending_moderation'
GROUP BY channel_moderator.res_users_id""", [tuple(self.ids)])
        result = dict(self._cr.fetchall())
        for user in self:
            user.moderation_counter = result.get(user.id, 0)

    def __init__(self, pool, cr):
        """ Override of __init__ to add access rights on notification_email_send
            fields. Access rights are disabled by default, but allowed on some
            specific fields defined in self.SELF_{READ/WRITE}ABLE_FIELDS.
        """
        init_res = super(Users, self).__init__(pool, cr)
        # duplicate list to avoid modifying the original reference
        type(self).SELF_WRITEABLE_FIELDS = list(self.SELF_WRITEABLE_FIELDS)
        type(self).SELF_WRITEABLE_FIELDS.extend(['notification_type'])
        # duplicate list to avoid modifying the original reference
        type(self).SELF_READABLE_FIELDS = list(self.SELF_READABLE_FIELDS)
        type(self).SELF_READABLE_FIELDS.extend(['notification_type'])
        return init_res

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if not values.get('login', False):
                action = self.env.ref('base.action_res_users')
                msg = _("You cannot create a new user from here.\n To create new user please go to configuration panel.")
                raise exceptions.RedirectWarning(msg, action.id, _('Go to the configuration panel'))

        users = super(Users, self).create(vals_list)
        # Auto-subscribe to channels
        self.env['mail.channel'].search([('group_ids', 'in', users.groups_id.ids)])._subscribe_users()
        return users

    def write(self, vals):
        write_res = super(Users, self).write(vals)
        if 'active' in vals and not vals['active']:
            self._unsubscribe_from_channels()
        sel_groups = [vals[k] for k in vals if is_selection_groups(k) and vals[k]]
        if vals.get('groups_id'):
            # form: {'group_ids': [(3, 10), (3, 3), (4, 10), (4, 3)]} or {'group_ids': [(6, 0, [ids]}
            user_group_ids = [command[1] for command in vals['groups_id'] if command[0] == 4]
            user_group_ids += [id for command in vals['groups_id'] if command[0] == 6 for id in command[2]]
            self.env['mail.channel'].search([('group_ids', 'in', user_group_ids)])._subscribe_users()
        elif sel_groups:
            self.env['mail.channel'].search([('group_ids', 'in', sel_groups)])._subscribe_users()
        return write_res

    def unlink(self):
        self._unsubscribe_from_channels()
        return super().unlink()

    def _unsubscribe_from_channels(self):
        """ This method un-subscribes users from private mail channels. Main purpose of this
            method is to prevent sending internal communication to archived / deleted users.
            We do not un-subscribes users from public channels because in most common cases,
            public channels are mailing list (e-mail based) and so users should always receive
            updates from public channels until they manually un-subscribe themselves.
        """
        self.mapped('partner_id.channel_ids').filtered(lambda c: c.public != 'public' and c.channel_type == 'channel').write({
            'channel_partner_ids': [(3, pid) for pid in self.mapped('partner_id').ids]
        })

    @api.model
    def systray_get_activities(self):
        activities = self.env["mail.activity"].search([("user_id", "=", self.env.uid)])
        activities_by_record_by_model_name = defaultdict(lambda: defaultdict(lambda: self.env["mail.activity"]))
        for activity in activities:
            record = self.env[activity.res_model].browse(activity.res_id)
            activities_by_record_by_model_name[activity.res_model][record] += activity
        model_ids = list({self.env["ir.model"]._get(name).id for name in activities_by_record_by_model_name.keys()})
        user_activities = {}
        for model_name, activities_by_record in activities_by_record_by_model_name.items():
            domain = [("id", "in", list({r.id for r in activities_by_record.keys()}))]
            allowed_records = self.env[model_name].search(domain)
            if not allowed_records:
                continue
            module = self.env[model_name]._original_module
            icon = module and modules.module.get_module_icon(module)
            user_activities[model_name] = {
                "name": self.env["ir.model"]._get(model_name).with_prefetch(model_ids).name,
                "model": model_name,
                "type": "activity",
                "icon": icon,
                "total_count": 0,
                "today_count": 0,
                "overdue_count": 0,
                "planned_count": 0,
                "actions": [
                    {
                        "icon": "fa-clock-o",
                        "name": "Summary",
                    }
                ],
            }
            for record, activities in activities_by_record.items():
                if record not in allowed_records:
                    continue
                for activity in activities:
                    user_activities[model_name]["%s_count" % activity.state] += 1
                    if activity.state in ("today", "overdue"):
                        user_activities[model_name]["total_count"] += 1
        return list(user_activities.values())


class res_groups_mail_channel(models.Model):
    """ Update of res.groups class
        - if adding users from a group, check mail.channels linked to this user
          group and subscribe them. This is done by overriding the write method.
    """
    _name = 'res.groups'
    _inherit = 'res.groups'
    _description = 'Access Groups'

    def write(self, vals, context=None):
        write_res = super(res_groups_mail_channel, self).write(vals)
        if vals.get('users'):
            # form: {'group_ids': [(3, 10), (3, 3), (4, 10), (4, 3)]} or {'group_ids': [(6, 0, [ids]}
            user_ids = [command[1] for command in vals['users'] if command[0] == 4]
            user_ids += [id for command in vals['users'] if command[0] == 6 for id in command[2]]
            self.env['mail.channel'].search([('group_ids', 'in', self._ids)])._subscribe_users()
        return write_res
