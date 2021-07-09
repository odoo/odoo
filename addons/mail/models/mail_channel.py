# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import logging
import re
from uuid import uuid4

from odoo import _, api, fields, models, modules, tools, Command
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import ormcache, formataddr

_logger = logging.getLogger(__name__)


class Channel(models.Model):
    """ A mail.channel is a discussion group that may behave like a listener
    on documents. """
    _description = 'Discussion Channel'
    _name = 'mail.channel'
    _mail_flat_thread = False
    _mail_post_access = 'read'
    _inherit = ['mail.thread', 'mail.alias.mixin']

    MAX_BOUNCE_LIMIT = 10

    @api.model
    def default_get(self, fields):
        res = super(Channel, self).default_get(fields)
        if not res.get('alias_contact') and (not fields or 'alias_contact' in fields):
            res['alias_contact'] = 'everyone' if res.get('public', 'private') == 'public' else 'followers'
        return res

    def _get_default_image(self):
        image_path = modules.get_module_resource('mail', 'static/src/img', 'groupdefault.png')
        return base64.b64encode(open(image_path, 'rb').read())

    # description
    name = fields.Char('Name', required=True, translate=True)
    active = fields.Boolean(default=True, help="Set active to false to hide the channel without removing it.")
    channel_type = fields.Selection([
        ('chat', 'Chat Discussion'),
        ('channel', 'Channel')],
        string='Channel Type', default='channel')
    is_chat = fields.Boolean(string='Is a chat', compute='_compute_is_chat')
    description = fields.Text('Description')
    image_128 = fields.Image("Image", max_width=128, max_height=128, default=_get_default_image)
    channel_partner_ids = fields.Many2many(
        'res.partner', string='Members',
        compute='_compute_channel_partner_ids', inverse='_inverse_channel_partner_ids',
        compute_sudo=True, search='_search_channel_partner_ids',
        groups='base.group_user')
    channel_last_seen_partner_ids = fields.One2many(
        'mail.channel.partner', 'channel_id', string='Last Seen',
        groups='base.group_user')
    is_member = fields.Boolean('Is Member', compute='_compute_is_member', compute_sudo=True)
    group_ids = fields.Many2many(
        'res.groups', string='Auto Subscription',
        help="Members of those groups will automatically added as followers. "
             "Note that they will be able to manage their subscription manually "
             "if necessary.")
    # access
    uuid = fields.Char('UUID', size=50, index=True, default=lambda self: str(uuid4()), copy=False)
    public = fields.Selection([
        ('public', 'Everyone'),
        ('private', 'Invited people only'),
        ('groups', 'Selected group of users')], string='Privacy',
        required=True, default='groups',
        help='This group is visible by non members. Invisible groups can add members through the invite button.')
    group_public_id = fields.Many2one('res.groups', string='Authorized Group',
                                      default=lambda self: self.env.ref('base.group_user'))
    # COMPUTE / INVERSE

    @api.depends('channel_type')
    def _compute_is_chat(self):
        for record in self:
            record.is_chat = record.channel_type == 'chat'

    @api.depends('channel_last_seen_partner_ids.partner_id')
    def _compute_channel_partner_ids(self):
        for channel in self:
            channel.channel_partner_ids = channel.channel_last_seen_partner_ids.partner_id

    def _inverse_channel_partner_ids(self):
        new_members = []
        outdated = self.env['mail.channel.partner']
        for channel in self:
            current_members = channel.channel_last_seen_partner_ids
            partners = channel.channel_partner_ids
            partners_new = partners - current_members.partner_id

            new_members += [{
                'channel_id': channel.id,
                'partner_id': partner.id,
            } for partner in partners_new]
            outdated += current_members.filtered(lambda m: m.partner_id not in partners)

        if new_members:
            self.env['mail.channel.partner'].create(new_members)
        if outdated:
            outdated.unlink()

    def _search_channel_partner_ids(self, operator, operand):
        return [(
            'channel_last_seen_partner_ids',
            'in',
            self.env['mail.channel.partner'].sudo()._search([
                ('partner_id', operator, operand)
            ])
        )]

    @api.depends('channel_partner_ids')
    def _compute_is_member(self):
        for channel in self:
            channel.is_member = self.env.user.partner_id in channel.channel_partner_ids

    # ONCHANGE

    @api.onchange('public')
    def _onchange_public(self):
        if self.public != 'public' and self.alias_contact == 'everyone':
            self.alias_contact = 'followers'

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        defaults = self.default_get(['image_128', 'public'])

        access_types = []
        for vals in vals_list:
            # find partners to add from partner_ids
            partner_ids_cmd = vals.get('channel_partner_ids') or []
            if any(cmd[0] not in (4, 6) for cmd in partner_ids_cmd):
                raise ValidationError(_('Invalid value when creating a channel with members, only 4 or 6 are allowed.'))
            partner_ids = [cmd[1] for cmd in partner_ids_cmd if cmd[0] == 4]
            partner_ids += [cmd[2] for cmd in partner_ids_cmd if cmd[0] == 6]

            # find partners to add from channel_last_seen_partner_ids
            membership_ids_cmd = vals.get('channel_last_seen_partner_ids') or []
            if any(cmd[0] != 0 for cmd in membership_ids_cmd):
                raise ValidationError(_('Invalid value when creating a channel with memberships, only 0 is allowed.'))
            membership_pids = [cmd[2]['partner_id'] for cmd in membership_ids_cmd if cmd[0] == 0]

            # always add current user to new channel to have right values for
            # is_pinned + ensure he has rights to see channel
            partner_ids_to_add = list(set(partner_ids + [self.env.user.partner_id.id]))
            vals['channel_last_seen_partner_ids'] = membership_ids_cmd + [
                (0, 0, {'partner_id': pid})
                for pid in partner_ids_to_add if pid not in membership_pids
            ]

            # ensure image at quick create
            if not vals.get('image_128'):
                vals['image_128'] = defaults['image_128']

            # save visibility, apply public visibility for create then set back after creation
            # to avoid ACLS issue
            access_type = vals.pop('public', defaults['public'])
            access_types.append(access_type)
            vals['public'] = 'public'
            if not vals.get('alias_contact') and access_type != 'public':
                vals['alias_contact'] = 'followers'

            # clean vals
            vals.pop('channel_partner_ids', False)

        # Create channel and alias
        channels = super(Channel, self.with_context(mail_create_nolog=True, mail_create_nosubscribe=True)).create(vals_list)

        for access_type, channel in zip(access_types, channels):
            if access_type != 'public':
                channel.sudo().public = access_type

        channels._subscribe_users_automatically()

        return channels

    @api.ondelete(at_uninstall=False)
    def _unlink_except_all_employee_channel(self):
        # Delete mail.channel
        try:
            all_emp_group = self.env.ref('mail.channel_all_employees')
        except ValueError:
            all_emp_group = None
        if all_emp_group and all_emp_group in self:
            raise UserError(_('You cannot delete those groups, as the Whole Company group is required by other modules.'))

    def write(self, vals):
        result = super(Channel, self).write(vals)

        if vals.get('group_ids'):
            self._subscribe_users_automatically()

        return result

    def init(self):
        self._cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('mail_channel_partner_seen_message_id_idx',))
        if not self._cr.fetchone():
            self._cr.execute('CREATE INDEX mail_channel_partner_seen_message_id_idx ON mail_channel_partner (channel_id,partner_id,seen_message_id)')

    # ------------------------------------------------------------
    # MEMBERS MANAGEMENT
    # ------------------------------------------------------------

    def _subscribe_users_automatically(self):
        new_members = self._subscribe_users_automatically_get_members()
        if new_members:
            to_create = [
                {'channel_id': channel_id, 'partner_id': partner_id}
                for channel_id in new_members
                for partner_id in new_members[channel_id]
            ]
            self.env['mail.channel.partner'].sudo().create(to_create)

    def _subscribe_users_automatically_get_members(self):
        """ Return new members per channel ID """
        return dict(
            (channel.id, (channel.group_ids.users.partner_id - channel.channel_partner_ids).ids)
            for channel in self
        )

    def action_follow(self):
        self.ensure_one()
        self.check_access_rights('write')
        self.check_access_rule('write')
        self._action_add_members(self.env.user.partner_id)
        return False

    def action_unfollow(self):
        return self._action_unfollow(self.env.user.partner_id)

    def _action_unfollow(self, partner):
        self.message_unsubscribe(partner.ids)
        if partner not in self.with_context(active_test=False).channel_partner_ids:
            return True
        channel_info = self.channel_info('unsubscribe')[0]  # must be computed before leaving the channel (access rights)
        result = self.write({'channel_partner_ids': [Command.unlink(partner.id)]})
        # side effect of unsubscribe that wasn't taken into account because
        # channel_info is called before actually unpinning the channel
        channel_info['is_pinned'] = False
        self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner', partner.id), channel_info)
        notification = _('<div class="o_mail_notification">left <a href="#" class="o_channel_redirect" data-oe-id="%s">#%s</a></div>', self.id, self.name)
        # post 'channel left' message as root since the partner just unsubscribed from the channel
        self.sudo().message_post(body=notification, subtype_xmlid="mail.mt_comment", author_id=partner.id)
        return result

    def _action_add_members(self, partners):
        """ Private implementation to add members to channels. Done as sudo to
        avoid ACLs issues with channel partners. """
        to_create = []
        for channel in self:
            channel_new = partners - channel.channel_partner_ids
            to_create += [
                {'partner_id': partner.id,
                 'channel_id': channel.id,
                } for partner in channel_new]
        if to_create:
            self.env['mail.channel.partner'].sudo().create(to_create)
            self.invalidate_cache(fnames=['channel_partner_ids', 'channel_last_seen_partner_ids'])

    def _action_remove_members(self, partners):
        """ Private implementation to remove members from channels. Done as sudo
        to avoid ACLs issues with channel partners. """
        self.env['mail.channel.partner'].sudo().search([
            ('partner_id', 'in', partners.ids),
            ('channel_id', 'in', self.ids)
        ]).unlink()
        self.invalidate_cache(fnames=['channel_partner_ids', 'channel_last_seen_partner_ids'])

    def channel_invite(self, partner_ids):
        """ Add the given partner_ids to the current channels and broadcast the channel header to them.
            :param partner_ids : list of partner id to add
        """
        partners = self.env['res.partner'].browse(partner_ids)
        self._invite_check_access(partners)

        # add the partner
        for channel in self:
            partners_to_add = partners - channel.channel_partner_ids
            channel.write({'channel_last_seen_partner_ids': [Command.create({'partner_id': partner_id}) for partner_id in partners_to_add.ids]})
            for partner in partners_to_add:
                if partner.id != self.env.user.partner_id.id:
                    notification = _('<div class="o_mail_notification">%(author)s invited %(new_partner)s to <a href="#" class="o_channel_redirect" data-oe-id="%(channel_id)s">#%(channel_name)s</a></div>',
                        author=self.env.user.display_name,
                        new_partner=partner.display_name,
                        channel_id=channel.id,
                        channel_name=channel.name,
                    )
                else:
                    notification = _('<div class="o_mail_notification">joined <a href="#" class="o_channel_redirect" data-oe-id="%s">#%s</a></div>', channel.id, channel.name)
                self.message_post(body=notification, message_type="notification", subtype_xmlid="mail.mt_comment", author_id=partner.id, notify_by_email=False)

        # broadcast the channel header to the added partner
        self._broadcast(partner_ids)

    def _invite_check_access(self, partners):
        """ Check invited partners could match channel access """
        failed = []
        if any(channel.public == 'groups' for channel in self):
            for channel in self.filtered(lambda c: c.public == 'groups'):
                invalid_partners = [partner for partner in partners if channel.group_public_id not in partner.mapped('user_ids.groups_id')]
                failed += [(channel, partner) for partner in invalid_partners]

        if failed:
            raise UserError(
                _('Following invites are invalid as user groups do not match: %s',
                  ', '.join('%s (channel %s)' % (partner.name, channel.name) for channel, partner in failed))
            )

    def _can_invite(self, partner_id):
        """Return True if the current user can invite the partner to the channel.

          * public: ok;
          * private: must be member;
          * group: both current user and target must have group;

        :return boolean: whether inviting is ok"""
        partner = self.env['res.partner'].browse(partner_id)

        for channel in self.sudo():
            if channel.public == 'private' and not channel.is_member:
                return False
            if channel.public == 'groups':
                if not partner.user_ids or channel.group_public_id not in partner.user_ids.groups_id:
                    return False
                if channel.group_public_id not in self.env.user.groups_id:
                    return False
        return True

    # ------------------------------------------------------------
    # MAILING
    # ------------------------------------------------------------

    def _alias_get_creation_values(self):
        values = super(Channel, self)._alias_get_creation_values()
        values['alias_model_id'] = self.env['ir.model']._get('mail.channel').id
        if self.id:
            values['alias_force_thread_id'] = self.id
        return values

    def _alias_get_error_message(self, message, message_dict, alias):
        if alias.alias_contact == 'followers' and self.ids:
            author = self.env['res.partner'].browse(message_dict.get('author_id', False))
            if not author or author not in self.channel_partner_ids:
                return _('restricted to channel members')
            return False
        return super(Channel, self)._alias_get_error_message(message, message_dict, alias)

    def _notify_compute_recipients(self, message, msg_vals):
        """ Override recipients computation as channel is not a standard
        mail.thread document. Indeed there are no followers on a channel.
        Instead of followers it has members that should be notified.

        :param message: see ``MailThread._notify_compute_recipients()``;
        :param msg_vals: see ``MailThread._notify_compute_recipients()``;

        :return recipients: structured data holding recipients data. See
          ``MailThread._notify_thread()`` for more details about its content
          and use;
        """
        # get values from msg_vals or from message if msg_vals doen't exists
        msg_sudo = message.sudo()
        message_type = msg_vals.get('message_type', 'email') if msg_vals else msg_sudo.message_type
        pids = msg_vals.get('partner_ids', []) if msg_vals else msg_sudo.partner_ids.ids

        # notify only user input (comment or incoming emails)
        if message_type not in ('comment', 'email'):
            return []
        # notify only mailing lists or if mentioning recipients
        if not pids:
            return []

        email_from = tools.email_normalize(msg_vals.get('email_from') or msg_sudo.email_from)
        author_id = msg_vals.get('author_id') or msg_sudo.author_id.id

        recipients_data = []
        if pids:
            sql_query = """
                SELECT DISTINCT ON (partner.id) partner.id,
                       partner.partner_share,
                       users.notification_type
                  FROM res_partner partner
             LEFT JOIN res_users users on partner.id = users.partner_id
                 WHERE partner.active IS TRUE
                       AND partner.email != %s
                       AND partner.id = ANY(%s) AND partner.id != ANY(%s)"""
            self.env.cr.execute(
                sql_query,
                (email_from, list(pids), [author_id] if author_id else [], )
            )
            for partner_id, partner_share, notif in self._cr.fetchall():
                # ocn_client: will add partners to recipient recipient_data. more ocn notifications. We neeed to filter them maybe
                recipients_data.append({
                    'id': partner_id,
                    'share': partner_share,
                    'active': True,
                    'notif': notif or 'email',
                    'type': 'user' if not partner_share and notif else 'customer',
                    'groups': [],
                })

        return recipients_data

    def _notify_get_groups(self, msg_vals=None):
        """ All recipients of a message on a channel are considered as partners.
        This means they will receive a minimal email, without a link to access
        in the backend. Mailing lists should indeed send minimal emails to avoid
        the noise. """
        groups = super(Channel, self)._notify_get_groups(msg_vals=msg_vals)
        for (index, (group_name, group_func, group_data)) in enumerate(groups):
            if group_name != 'customer':
                groups[index] = (group_name, lambda partner: False, group_data)
        return groups

    def _notify_email_header_dict(self):
        headers = super(Channel, self)._notify_email_header_dict()
        headers['Precedence'] = 'list'
        # avoid out-of-office replies from MS Exchange
        # http://blogs.technet.com/b/exchange/archive/2006/10/06/3395024.aspx
        headers['X-Auto-Response-Suppress'] = 'OOF'
        if self.alias_domain and self.alias_name:
            headers['List-Id'] = '<%s.%s>' % (self.alias_name, self.alias_domain)
            headers['List-Post'] = '<mailto:%s@%s>' % (self.alias_name, self.alias_domain)
            # Avoid users thinking it was a personal message
            # X-Forge-To: will replace To: after SMTP envelope is determined by ir.mail.server
            list_to = '"%s" <%s@%s>' % (self.name, self.alias_name, self.alias_domain)
            headers['X-Forge-To'] = list_to
        return headers

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        # link message to channel
        rdata = super(Channel, self)._notify_thread(message, msg_vals=msg_vals, **kwargs)

        message_format_values = message.message_format()[0]
        bus_notifications = self._channel_message_notifications(message, message_format_values)
        self.env['bus.bus'].sudo().sendmany(bus_notifications)
        return rdata

    def _message_receive_bounce(self, email, partner):
        """ Override bounce management to unsubscribe bouncing addresses """
        for p in partner:
            if p.message_bounce >= self.MAX_BOUNCE_LIMIT:
                self._action_unfollow(p)
        return super(Channel, self)._message_receive_bounce(email, partner)

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, *, message_type='notification', **kwargs):
        self.filtered(lambda channel: channel.is_chat).mapped('channel_last_seen_partner_ids').sudo().write({'is_pinned': True})

        # mail_post_autofollow=False is necessary to prevent adding followers
        # when using mentions in channels. Followers should not be added to
        # channels, and especially not automatically (because channel membership
        # should be managed with channel.partner instead).
        # The current client code might be setting the key to True on sending
        # message but it is only useful when targeting customers in chatter.
        # This value should simply be set to False in channels no matter what.
        return super(Channel, self.with_context(mail_create_nosubscribe=True, mail_post_autofollow=False)).message_post(message_type=message_type, **kwargs)

    def _message_post_after_hook(self, message, msg_vals):
        """
        Automatically set the message posted by the current user as seen for himself.
        """
        self._set_last_seen_message(message)
        return super()._message_post_after_hook(message=message, msg_vals=msg_vals)

    def _message_subscribe(self, partner_ids=None, subtype_ids=None, customer_ids=None):
        """ Do not allow follower subscription on channels. Only members are
        considered. """
        raise UserError(_('Adding followers on channels is not possible. Consider adding members instead.'))

    # ------------------------------------------------------------
    # BROADCAST
    # ------------------------------------------------------------

    # Anonymous method
    def _broadcast(self, partner_ids):
        """ Broadcast the current channel header to the given partner ids
            :param partner_ids : the partner to notify
        """
        notifications = self._channel_channel_notifications(partner_ids)
        self.env['bus.bus'].sendmany(notifications)

    def _channel_channel_notifications(self, partner_ids):
        """ Generate the bus notifications of current channel for the given partner ids
            :param partner_ids : the partner to send the current channel header
            :returns list of bus notifications (tuple (bus_channe, message_content))
        """
        notifications = []
        for partner in self.env['res.partner'].browse(partner_ids):
            user_id = partner.user_ids and partner.user_ids[0] or False
            if user_id:
                user_channels = self.with_user(user_id).with_context(
                    allowed_company_ids=user_id.company_ids.ids
                )
                for channel_info in user_channels.channel_info():
                    notifications.append([(self._cr.dbname, 'res.partner', partner.id), channel_info])
        return notifications

    def _channel_message_notifications(self, message, message_format=False):
        """ Generate the bus notifications for the given message
            :param message : the mail.message to sent
            :returns list of bus notifications (tuple (bus_channe, message_content))
        """
        message_format = message_format or message.message_format()[0]
        notifications = []
        for channel in self:
            notifications.append([(self._cr.dbname, 'mail.channel', channel.id), dict(message_format)])
            # add uuid to allow anonymous to listen
            if channel.public == 'public':
                notifications.append([channel.uuid, dict(message_format)])
        return notifications

    # ------------------------------------------------------------
    # INSTANT MESSAGING API
    # ------------------------------------------------------------
    # A channel header should be broadcasted:
    #   - when adding user to channel (only to the new added partners)
    #   - when folding/minimizing a channel (only to the user making the action)
    # A message should be broadcasted:
    #   - when a message is posted on a channel (to the channel, using _notify() method)
    # ------------------------------------------------------------

    @api.model
    def _get_channel_partner_info(self, all_partners, direct_partners):
        """
        Return the information needed by channel to display channel members
            :param all_partners: list of res.parner():
            :param direct_partners: list of res.parner():
            :returns: a list of {'id', 'name', 'email'} for each partner and adds {im_status} for direct_partners.
            :rtype : list(dict)
        """
        partner_infos = {partner['id']: partner for partner in all_partners.sudo().read(['id', 'name', 'email'])}
        # add im _status for direct_partners
        direct_partners_im_status = {partner['id']: partner for partner in direct_partners.sudo().read(['im_status'])}

        for i in direct_partners_im_status.keys():
            partner_infos[i].update(direct_partners_im_status[i])

        return partner_infos

    def channel_info(self, extra_info=False):
        """ Get the informations header for the current channels
            :returns a list of channels values
            :rtype : list(dict)
        """
        if not self:
            return []
        channel_infos = []
        # all relations partner_channel on those channels
        all_partner_channel = self.env['mail.channel.partner'].search([('channel_id', 'in', self.ids)])

        # all partner infos on those channels
        channel_dict = {channel.id: channel for channel in self}
        all_partners = all_partner_channel.mapped('partner_id')
        direct_channel_partners = all_partner_channel.filtered(lambda pc: channel_dict[pc.channel_id.id].channel_type == 'chat')
        direct_partners = direct_channel_partners.mapped('partner_id')
        partner_infos = self._get_channel_partner_info(all_partners, direct_partners)
        channel_last_message_ids = dict((r['id'], r['message_id']) for r in self._channel_last_message_ids())

        for channel in self:
            info = {
                'id': channel.id,
                'name': channel.name,
                'uuid': channel.uuid,
                'state': 'open',
                'is_minimized': False,
                'channel_type': channel.channel_type,
                'public': channel.public,
                'group_based_subscription': bool(channel.group_ids),
                'create_uid': channel.create_uid.id,
            }
            if extra_info:
                info['info'] = extra_info

            # add last message preview (only used in mobile)
            info['last_message_id'] = channel_last_message_ids.get(channel.id, False)
            # listeners of the channel
            channel_partners = all_partner_channel.filtered(lambda pc: channel.id == pc.channel_id.id)

            # find the channel partner state, if logged user
            if self.env.user and self.env.user.partner_id:
                # add needaction and unread counter, since the user is logged
                info['message_needaction_counter'] = channel.message_needaction_counter
                info['message_unread_counter'] = channel.message_unread_counter

                # add user session state, if available and if user is logged
                partner_channel = channel_partners.filtered(lambda pc: pc.partner_id.id == self.env.user.partner_id.id)
                if partner_channel:
                    partner_channel = partner_channel[0]
                    info['state'] = partner_channel.fold_state or 'open'
                    info['is_minimized'] = partner_channel.is_minimized
                    info['seen_message_id'] = partner_channel.seen_message_id.id
                    info['custom_channel_name'] = partner_channel.custom_channel_name
                    info['is_pinned'] = partner_channel.is_pinned

            # add members infos
            if channel.channel_type != 'channel':
                # avoid sending potentially a lot of members for big channels
                # exclude chat and other small channels from this optimization because they are
                # assumed to be smaller and it's important to know the member list for them
                partner_ids = channel_partners.mapped('partner_id').ids
                info['members'] = [partner_infos[partner] for partner in partner_ids]
            if channel.channel_type != 'channel':
                info['seen_partners_info'] = [{
                    'id': cp.id,
                    'partner_id': cp.partner_id.id,
                    'fetched_message_id': cp.fetched_message_id.id,
                    'seen_message_id': cp.seen_message_id.id,
                } for cp in channel_partners]

            channel_infos.append(info)
        return channel_infos

    def channel_fetch_message(self, last_id=False, limit=20):
        """ Return message values of the current channel.
            :param last_id : last message id to start the research
            :param limit : maximum number of messages to fetch
            :returns list of messages values
            :rtype : list(dict)
        """
        self.ensure_one()
        domain = ["&", ("model", "=", "mail.channel"), ("res_id", "in", self.ids)]
        if last_id:
            domain.append(("id", "<", last_id))
        return self.env['mail.message'].message_fetch(domain=domain, limit=limit)

    # User methods
    @api.model
    def channel_get(self, partners_to, pin=True):
        """ Get the canonical private channel between some partners, create it if needed.
            To reuse an old channel (conversation), this one must be private, and contains
            only the given partners.
            :param partners_to : list of res.partner ids to add to the conversation
            :param pin : True if getting the channel should pin it for the current user
            :returns: channel_info of the created or existing channel
            :rtype: dict
        """
        if self.env.user.partner_id.id not in partners_to:
            partners_to.append(self.env.user.partner_id.id)
        # determine type according to the number of partner in the channel
        self.flush()
        self.env.cr.execute("""
            SELECT P.channel_id
            FROM mail_channel C, mail_channel_partner P
            WHERE P.channel_id = C.id
                AND C.public LIKE 'private'
                AND P.partner_id IN %s
                AND C.channel_type LIKE 'chat'
                AND NOT EXISTS (
                    SELECT *
                    FROM mail_channel_partner P2
                    WHERE P2.channel_id = C.id
                        AND P2.partner_id NOT IN %s
                )
            GROUP BY P.channel_id
            HAVING ARRAY_AGG(DISTINCT P.partner_id ORDER BY P.partner_id) = %s
            LIMIT 1
        """, (tuple(partners_to), tuple(partners_to), sorted(list(partners_to)),))
        result = self.env.cr.dictfetchall()
        if result:
            # get the existing channel between the given partners
            channel = self.browse(result[0].get('channel_id'))
            # pin up the channel for the current partner
            if pin:
                self.env['mail.channel.partner'].search([('partner_id', '=', self.env.user.partner_id.id), ('channel_id', '=', channel.id)]).write({'is_pinned': True})
            channel._broadcast(self.env.user.partner_id.ids)
        else:
            # create a new one
            channel = self.create({
                'channel_partner_ids': [Command.link(partner_id) for partner_id in partners_to],
                'public': 'private',
                'channel_type': 'chat',
                'name': ', '.join(self.env['res.partner'].sudo().browse(partners_to).mapped('name')),
            })
            channel._broadcast(partners_to)
        return channel.channel_info()[0]

    @api.model
    def channel_get_and_minimize(self, partners_to):
        channel = self.channel_get(partners_to)
        if channel:
            self.channel_minimize(channel['uuid'])
        return channel

    @api.model
    def channel_fold(self, uuid, state=None):
        """ Update the fold_state of the given session. In order to syncronize web browser
            tabs, the change will be broadcast to himself (the current user channel).
            Note: the user need to be logged
            :param state : the new status of the session for the current user.
        """
        domain = [('partner_id', '=', self.env.user.partner_id.id), ('channel_id.uuid', '=', uuid)]
        for session_state in self.env['mail.channel.partner'].search(domain):
            if not state:
                state = session_state.fold_state
                if session_state.fold_state == 'open':
                    state = 'folded'
                else:
                    state = 'open'
            session_state.write({
                'fold_state': state,
                'is_minimized': bool(state != 'closed'),
            })
            self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner', self.env.user.partner_id.id), session_state.channel_id.channel_info()[0])

    @api.model
    def channel_minimize(self, uuid, minimized=True):
        values = {
            'fold_state': minimized and 'open' or 'closed',
            'is_minimized': minimized
        }
        domain = [('partner_id', '=', self.env.user.partner_id.id), ('channel_id.uuid', '=', uuid)]
        channel_partners = self.env['mail.channel.partner'].search(domain, limit=1)
        channel_partners.write(values)
        self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner', self.env.user.partner_id.id), channel_partners.channel_id.channel_info()[0])

    @api.model
    def channel_pin(self, uuid, pinned=False):
        # add the person in the channel, and pin it (or unpin it)
        channel = self.search([('uuid', '=', uuid)])
        channel._execute_channel_pin(pinned)

    def _execute_channel_pin(self, pinned=False):
        """ Hook for website_livechat channel unpin and cleaning """
        self.ensure_one()
        channel_partners = self.env['mail.channel.partner'].search(
            [('partner_id', '=', self.env.user.partner_id.id), ('channel_id', '=', self.id), ('is_pinned', '!=', pinned)])
        self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner', self.env.user.partner_id.id), self.channel_info('unsubscribe' if not pinned else False)[0])
        if channel_partners:
            channel_partners.write({'is_pinned': pinned})

    def channel_seen(self, last_message_id=None):
        """
        Mark channel as seen by updating seen message id of the current logged partner
        :param last_message_id: the id of the message to be marked as seen, last message of the
        thread by default. This param SHOULD be required, the default behaviour is DEPRECATED and
        kept only for compatibility reasons.
        """
        self.ensure_one()
        domain = ["&", ("model", "=", "mail.channel"), ("res_id", "in", self.ids)]
        if last_message_id:
            domain = expression.AND([domain, [('id', '<=', last_message_id)]])
        last_message = self.env['mail.message'].search(domain, order="id DESC", limit=1)
        if not last_message:
            return

        self._set_last_seen_message(last_message)

        data = {
            'info': 'channel_seen',
            'last_message_id': last_message.id,
            'partner_id': self.env.user.partner_id.id,
        }
        if self.channel_type == 'chat':
            self.env['bus.bus'].sendmany([[(self._cr.dbname, 'mail.channel', self.id), data]])
        else:
            data['channel_id'] = self.id
            self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner', self.env.user.partner_id.id), data)
        return last_message.id

    def _set_last_seen_message(self, last_message):
        """
        Set last seen message of `self` channels for the current user.
        :param last_message: the message to set as last seen message
        """
        channel_partner_domain = expression.AND([
            [('channel_id', 'in', self.ids)],
            [('partner_id', '=', self.env.user.partner_id.id)],
            expression.OR([
                [('seen_message_id', '=', False)],
                [('seen_message_id', '<', last_message.id)]
            ])
        ])
        channel_partner = self.env['mail.channel.partner'].search(channel_partner_domain)
        channel_partner.write({
            'fetched_message_id': last_message.id,
            'seen_message_id': last_message.id,
        })

    def channel_fetched(self):
        """ Broadcast the channel_fetched notification to channel members
        """
        for channel in self:
            if not channel.message_ids.ids:
                return
            if channel.channel_type != 'chat':
                return
            last_message_id = channel.message_ids.ids[0] # zero is the index of the last message
            channel_partner = self.env['mail.channel.partner'].search([('channel_id', '=', channel.id), ('partner_id', '=', self.env.user.partner_id.id)], limit=1)
            if channel_partner.fetched_message_id.id == last_message_id:
                # last message fetched by user is already up-to-date
                return
            channel_partner.write({
                'fetched_message_id': last_message_id,
            })
            data = {
                'id': channel_partner.id,
                'info': 'channel_fetched',
                'last_message_id': last_message_id,
                'partner_id': self.env.user.partner_id.id,
            }
            self.env['bus.bus'].sendmany([[(self._cr.dbname, 'mail.channel', channel.id), data]])

    @api.model
    def channel_set_custom_name(self, channel_id, name=False):
        domain = [('partner_id', '=', self.env.user.partner_id.id), ('channel_id.id', '=', channel_id)]
        channel_partners = self.env['mail.channel.partner'].search(domain, limit=1)
        channel_partners.write({
            'custom_channel_name': name,
        })

    def notify_typing(self, is_typing):
        """ Broadcast the typing notification to channel members
            :param is_typing: (boolean) tells whether the current user is typing or not
        """
        notifications = []
        for channel in self:
            data = {
                'info': 'typing_status',
                'is_typing': is_typing,
                'partner_id': self.env.user.partner_id.id,
                'partner_name': self.env.user.partner_id.name,
            }
            notifications.append([(self._cr.dbname, 'mail.channel', channel.id), data]) # notify backend users
            notifications.append([channel.uuid, data]) # notify frontend users
        self.env['bus.bus'].sendmany(notifications)

    # ------------------------------------------------------------
    # IM VIEW SPECIFIC (Slack Client Action)
    # ------------------------------------------------------------

    @api.model
    def channel_fetch_slot(self):
        """ Return the channels of the user grouped by 'slot' (channel, direct_message or private_group), and
            the mapping between partner_id/channel_id for direct_message channels.
            :returns dict : the grouped channels and the mapping
        """
        values = {}
        my_partner_id = self.env.user.partner_id.id
        pinned_channels = self.env['mail.channel.partner'].search([('partner_id', '=', my_partner_id), ('is_pinned', '=', True)]).mapped('channel_id')

        # get the group/public channels
        values['channel_channel'] = self.search([('channel_type', '=', 'channel'), ('public', 'in', ['public', 'groups']), ('channel_partner_ids', 'in', [my_partner_id])]).channel_info()

        # get the pinned 'direct message' channel
        direct_message_channels = self.search([('channel_type', '=', 'chat'), ('id', 'in', pinned_channels.ids)])
        values['channel_direct_message'] = direct_message_channels.channel_info()

        # get the private group
        values['channel_private_group'] = self.search([('channel_type', '=', 'channel'), ('public', '=', 'private'), ('channel_partner_ids', 'in', [my_partner_id])]).channel_info()
        return values

    @api.model
    def channel_search_to_join(self, name=None, domain=None):
        """ Return the channel info of the channel the current partner can join
            :param name : the name of the researched channels
            :param domain : the base domain of the research
            :returns dict : channel dict
        """
        if not domain:
            domain = []
        domain = expression.AND([
            [('channel_type', '=', 'channel')],
            [('channel_partner_ids', 'not in', [self.env.user.partner_id.id])],
            [('public', '!=', 'private')],
            domain
        ])
        if name:
            domain = expression.AND([domain, [('name', 'ilike', '%'+name+'%')]])
        return self.search(domain).read(['name', 'public', 'uuid', 'channel_type'])

    def channel_join_and_get_info(self):
        self.ensure_one()
        added = self.action_follow()
        if added and self.channel_type == 'channel':
            notification = _('<div class="o_mail_notification">joined <a href="#" class="o_channel_redirect" data-oe-id="%s">#%s</a></div>', self.id, self.name)
            self.message_post(body=notification, message_type="notification", subtype_xmlid="mail.mt_comment")

        channel_info = self.channel_info('join')[0]
        self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner', self.env.user.partner_id.id), channel_info)
        return channel_info

    @api.model
    def channel_create(self, name, privacy='public'):
        """ Create a channel and add the current partner, broadcast it (to make the user directly
            listen to it when polling)
            :param name : the name of the channel to create
            :param privacy : privacy of the channel. Should be 'public' or 'private'.
            :return dict : channel header
        """
        # create the channel
        new_channel = self.create({
            'name': name,
            'public': privacy,
        })
        notification = _('<div class="o_mail_notification">created <a href="#" class="o_channel_redirect" data-oe-id="%s">#%s</a></div>', new_channel.id, new_channel.name)
        new_channel.message_post(body=notification, message_type="notification", subtype_xmlid="mail.mt_comment")
        channel_info = new_channel.channel_info('creation')[0]
        self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner', self.env.user.partner_id.id), channel_info)
        return channel_info

    @api.model
    def get_mention_suggestions(self, search, limit=8):
        """ Return 'limit'-first channels' id, name and public fields such that the name matches a
            'search' string. Exclude channels of type chat (DM), and private channels the current
            user isn't registered to. """
        domain = expression.AND([
                        [('name', 'ilike', search)],
                        [('channel_type', '=', 'channel')],
                        expression.OR([
                            [('public', '!=', 'private')],
                            [('channel_partner_ids', 'in', [self.env.user.partner_id.id])]
                        ])
                    ])
        return self.search_read(domain, ['id', 'name', 'public', 'channel_type'], limit=limit)

    @api.model
    def channel_fetch_listeners(self, uuid):
        """ Return the id, name and email of partners listening to the given channel """
        self._cr.execute("""
            SELECT P.id, P.name, P.email
            FROM mail_channel_partner CP
                INNER JOIN res_partner P ON CP.partner_id = P.id
                INNER JOIN mail_channel C ON CP.channel_id = C.id
            WHERE C.uuid = %s""", (uuid,))
        return self._cr.dictfetchall()

    def channel_fetch_preview(self):
        """ Return the last message of the given channels """
        if not self:
            return []
        channels_last_message_ids = self._channel_last_message_ids()
        channels_preview = dict((r['message_id'], r) for r in channels_last_message_ids)
        last_messages = self.env['mail.message'].browse(channels_preview).message_format()
        for message in last_messages:
            channel = channels_preview[message['id']]
            del(channel['message_id'])
            channel['last_message'] = message
        return list(channels_preview.values())

    def _channel_last_message_ids(self):
        """ Return the last message of the given channels."""
        if not self:
            return []
        self.flush()
        self.env.cr.execute("""
            SELECT res_id AS id, MAX(id) AS message_id
            FROM mail_message
            WHERE model = 'mail.channel' AND res_id IN %s
            GROUP BY res_id
            """, (tuple(self.ids),))
        return self.env.cr.dictfetchall()

    # ------------------------------------------------------------
    # COMMANDS
    # ------------------------------------------------------------

    @api.model
    @ormcache()
    def get_mention_commands(self):
        """ Returns the allowed commands in channels """
        commands = []
        for n in dir(self):
            match = re.search('^_define_command_(.+?)$', n)
            if match:
                command = getattr(self, n)()
                command['name'] = match.group(1)
                commands.append(command)
        return commands

    def execute_command(self, command='', **kwargs):
        """ Executes a given command """
        self.ensure_one()
        command_callback = getattr(self, '_execute_command_' + command, False)
        if command_callback:
            command_callback(**kwargs)

    def _send_transient_message(self, partner_to, content):
        """ Notifies partner_to that a message (not stored in DB) has been
            written in this channel """
        self.env['bus.bus'].sendone(
            (self._cr.dbname, 'res.partner', partner_to.id),
            {'body': "<span class='o_mail_notification'>" + content + "</span>",
             'info': 'transient_message',
             'model': self._name,
             'res_id': self.id,
            }
        )

    def _define_command_help(self):
        return {'help': _("Show a helper message")}

    def _execute_command_help(self, **kwargs):
        partner = self.env.user.partner_id
        if self.channel_type == 'channel':
            msg = _("You are in channel <b>#%s</b>.", self.name)
            if self.public == 'private':
                msg += _(" This channel is private. People must be invited to join it.")
        else:
            all_channel_partners = self.env['mail.channel.partner'].with_context(active_test=False)
            channel_partners = all_channel_partners.search([('partner_id', '!=', partner.id), ('channel_id', '=', self.id)])
            msg = _("You are in a private conversation with <b>@%s</b>.", channel_partners[0].partner_id.name if channel_partners else _('Anonymous'))
        msg += self._execute_command_help_message_extra()

        self._send_transient_message(partner, msg)

    def _define_command_leave(self):
        return {'help': _("Leave this channel")}

    def _execute_command_help_message_extra(self):
        msg = _("""<br><br>
            Type <b>@username</b> to mention someone, and grab his attention.<br>
            Type <b>#channel</b> to mention a channel.<br>
            Type <b>/command</b> to execute a command.<br>""")
        return msg

    def _execute_command_leave(self, **kwargs):
        if self.channel_type == 'channel':
            self.action_unfollow()
        else:
            self.channel_pin(self.uuid, False)

    def _define_command_who(self):
        return {
            'channel_types': ['channel', 'chat'],
            'help': _("List users in the current channel")
        }

    def _execute_command_who(self, **kwargs):
        partner = self.env.user.partner_id
        members = [
            '<a href="#" data-oe-id='+str(p.id)+' data-oe-model="res.partner">@'+p.name+'</a>'
            for p in self.channel_partner_ids[:30] if p != partner
        ]
        if len(members) == 0:
            msg = _("You are alone in this channel.")
        else:
            dots = "..." if len(members) != len(self.channel_partner_ids) - 1 else ""
            msg = _("Users in this channel: %(members)s %(dots)s and you.", members=", ".join(members), dots=dots)

        self._send_transient_message(partner, msg)
