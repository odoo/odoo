# -*- coding: utf-8 -*-

import datetime
import time
import uuid

from openerp import _, api, fields, models, modules, tools
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.exceptions import UserError
from openerp.osv import expression

from openerp.addons.bus.models.bus_presence import AWAY_TIMER


class ChannelPartner(models.Model):
    _name = 'mail.channel.partner'
    _description = 'Last Seen Many2many'
    _table = 'mail_channel_partner'
    _rec_name = 'partner_id'

    partner_id = fields.Many2one('res.partner', string='Recipient')
    channel_id = fields.Many2one('mail.channel', string='Channel')
    seen_message_id = fields.Many2one('mail.message', string='Last Seen')
    fold_state = fields.Selection([('open', 'Open'), ('folded', 'Folded'), ('closed', 'Closed')], string='Conversation Fold State', default='open')
    is_minimized = fields.Boolean("Conversation is minimied")
    is_pinned = fields.Boolean("Is pinned on the interface", default=True)


class Channel(models.Model):
    """ A mail.channel is a discussion group that may behave like a listener
    on documents. """
    _description = 'Discussion channel'
    _name = 'mail.channel'
    _mail_flat_thread = False
    _mail_post_access = 'read'
    _inherit = ['mail.thread']
    _inherits = {'mail.alias': 'alias_id'}

    def _get_default_image(self):
        image_path = modules.get_module_resource('mail', 'static/src/img', 'groupdefault.png')
        return tools.image_resize_image_big(open(image_path, 'rb').read().encode('base64'))

    name = fields.Char('Name', required=True, translate=True)
    channel_type = fields.Selection([
        ('chat', 'Chat Discussion'),
        ('channel', 'Channel')],
        'Channel Type', default='channel')
    description = fields.Text('Description')
    uuid = fields.Char('UUID', size=50, select=True, default=lambda self: '%s' % uuid.uuid4())
    email_send = fields.Boolean('Email Sent', default=True)
    # multi users channel
    channel_last_seen_partner_ids = fields.One2many('mail.channel.partner', 'channel_id', string='Last Seen')
    channel_partner_ids = fields.Many2many('res.partner', 'mail_channel_partner', 'channel_id', 'partner_id', string='Listeners')
    channel_message_ids = fields.Many2many('mail.message', 'mail_message_mail_channel_rel')
    # access
    public = fields.Selection([
        ('public', 'Everyone'),
        ('private', 'Invited people only'),
        ('groups', 'Selected group of users')],
        'Privacy', required=True, default='groups',
        help='This group is visible by non members. Invisible groups can add members through the invite button.')
    group_public_id = fields.Many2one('res.groups', string='Authorized Group',
                                      default=lambda self: self.env.ref('base.group_user'))
    group_ids = fields.Many2many(
        'res.groups', rel='mail_channel_res_group_rel',
        id1='mail_channel_id', id2='groups_id', string='Auto Subscription',
        help="Members of those groups will automatically added as followers. "
             "Note that they will be able to manage their subscription manually "
             "if necessary.")
    # image: all image fields are base64 encoded and PIL-supported
    image = fields.Binary("Photo", default=_get_default_image, attachment=True,
        help="This field holds the image used as photo for the group, limited to 1024x1024px.")
    image_medium = fields.Binary('Medium-sized photo',
        compute='_get_image', inverse='_set_image_medium', store=True, attachment=True,
        help="Medium-sized photo of the group. It is automatically "
             "resized as a 128x128px image, with aspect ratio preserved. "
             "Use this field in form views or some kanban views.")
    image_small = fields.Binary('Small-sized photo',
        compute='_get_image', inverse='_set_image_small', store=True, attachment=True,
        help="Small-sized photo of the group. It is automatically "
             "resized as a 64x64px image, with aspect ratio preserved. "
             "Use this field anywhere a small image is required.")
    alias_id = fields.Many2one(
        'mail.alias', 'Alias', ondelete="restrict", required=True,
        help="The email address associated with this group. New emails received will automatically create new topics.")

    @api.one
    @api.depends('image')
    def _get_image(self):
        self.image_medium = tools.image_resize_image_medium(self.image)
        self.image_small = tools.image_resize_image_small(self.image)

    def _set_image_medium(self):
        self.image = tools.image_resize_image_big(self.image_medium)

    def _set_image_small(self):
        self.image = tools.image_resize_image_big(self.image_small)

    @api.model
    def create(self, vals):
        # Create channel and alias
        channel = super(Channel, self.with_context(
            alias_model_name=self._name, alias_parent_model_name=self._name, mail_create_nolog=True, mail_create_nosubscribe=True)
        ).create(vals)
        channel.alias_id.write({"alias_force_thread_id": channel.id, 'alias_parent_thread_id': channel.id})

        if vals.get('group_ids'):
            channel._subscribe_users()

        # make channel listen itself: posting on a channel notifies the channel
        if not self._context.get('mail_channel_noautofollow'):
            channel.message_subscribe(channel_ids=[channel.id])

        return channel

    @api.multi
    def unlink(self):
        aliases = self.mapped('alias_id')

        # Delete mail.channel
        try:
            all_emp_group = self.env.ref('mail.channel_all_employees')
        except ValueError:
            all_emp_group = None
        if all_emp_group and all_emp_group in self:
            raise UserError(_('You cannot delete those groups, as the Whole Company group is required by other modules.'))
        res = super(Channel, self).unlink()
        # Cascade-delete mail aliases as well, as they should not exist without the mail.channel.
        aliases.sudo().unlink()
        return res

    @api.multi
    def write(self, vals):
        result = super(Channel, self).write(vals)
        if vals.get('group_ids'):
            self._subscribe_users()
        return result

    def _subscribe_users(self):
        for mail_channel in self:
            mail_channel.write({'channel_partner_ids': [(4, pid) for pid in mail_channel.mapped('group_ids').mapped('users').mapped('partner_id').ids]})

    @api.multi
    def action_follow(self):
        self.ensure_one()
        channel_partner = self.mapped('channel_last_seen_partner_ids').filtered(lambda cp: cp.partner_id == self.env.user.partner_id)
        if not channel_partner:
            return self.write({'channel_last_seen_partner_ids': [(0, 0, {'partner_id': self.env.user.partner_id.id})]})

    @api.multi
    def action_unfollow(self):
        result = self.write({'channel_partner_ids': [(3, self.env.user.partner_id.id)]})
        self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner', self.env.user.partner_id.id), self.channel_info('unsubscribe')[0])
        notification = _('<div class="o_mail_notification">left <a href="#" class="o_channel_redirect" data-oe-id="%s">#%s</a></div>') % (self.id, self.name,)
        self.message_post(body=notification, message_type="notification", subtype="mail.mt_comment")
        return result


    @api.multi
    def message_get_email_values(self, notif_mail=None):
        self.ensure_one()
        res = super(Channel, self).message_get_email_values(notif_mail=notif_mail)
        headers = {}
        if res.get('headers'):
            try:
                headers.update(eval(res['headers']))
            except Exception:
                pass
        headers['Precedence'] = 'list'
        # avoid out-of-office replies from MS Exchange
        # http://blogs.technet.com/b/exchange/archive/2006/10/06/3395024.aspx
        headers['X-Auto-Response-Suppress'] = 'OOF'
        if self.alias_domain and self.alias_name:
            headers['List-Id'] = '%s.%s' % (self.alias_name, self.alias_domain)
            headers['List-Post'] = '<mailto:%s@%s>' % (self.alias_name, self.alias_domain)
            # Avoid users thinking it was a personal message
            # X-Forge-To: will replace To: after SMTP envelope is determined by ir.mail.server
            list_to = '"%s" <%s@%s>' % (self.name, self.alias_name, self.alias_domain)
            headers['X-Forge-To'] = list_to
        res['headers'] = repr(headers)
        return res

    @api.multi
    @api.returns('self', lambda value: value.id)
    def message_post(self, body='', subject=None, message_type='notification', subtype=None, parent_id=False, attachments=None, content_subtype='html', **kwargs):
        # auto pin 'direct_message' channel partner
        self.filtered(lambda channel: channel.channel_type == 'direct_message').mapped('channel_last_seen_partner_ids').write({'is_pinned': True})
        # apply shortcode (text only) subsitution
        body = self.env['mail.shortcode'].apply_shortcode(body, shortcode_type='text')
        message = super(Channel, self.with_context(mail_create_nosubscribe=True)).message_post(body=body, subject=subject, message_type=message_type, subtype=subtype, parent_id=parent_id, attachments=attachments, content_subtype=content_subtype, **kwargs)
        return message

    #------------------------------------------------------
    # Instant Messaging API
    #------------------------------------------------------
    # A channel header should be broadcasted:
    #   - when adding user to channel (only to the new added partners)
    #   - when folding/minimizing a channel (only to the user making the action)
    # A message should be broadcasted:
    #   - when a message is posted on a channel (to the channel, using _notify() method)

    # Anonymous method
    @api.multi
    def _broadcast(self, partner_ids):
        """ Broadcast the current channel header to the given partner ids
            :param partner_ids : the partner to notify
        """
        notifications = self._channel_channel_notifications(partner_ids)
        self.env['bus.bus'].sendmany(notifications)

    @api.multi
    def _channel_channel_notifications(self, partner_ids):
        """ Generate the bus notifications of current channel for the given partner ids
            :param partner_ids : the partner to send the current channel header
            :returns list of bus notifications (tuple (bus_channe, message_content))
        """
        notifications = []
        for partner in self.env['res.partner'].browse(partner_ids):
            user_id = partner.user_ids and partner.user_ids[0] or False
            if user_id:
                for channel_info in self.sudo(user_id).channel_info():
                    notifications.append([(self._cr.dbname, 'res.partner', partner.id), channel_info])
        return notifications

    @api.multi
    def _notify(self, message):
        """ Broadcast the given message on the current channels.
            Send the message on the Bus Channel (uuid for public mail.channel, and partner private bus channel (the tuple)).
            A partner will receive only on message on its bus channel, even if this message belongs to multiple mail channel. Then 'channel_ids' field
            of the received message indicates on wich mail channel the message should be displayed.
            :param : mail.message to broadcast
        """
        message.ensure_one()
        notifications = self._channel_message_notifications(message)
        self.env['bus.bus'].sendmany(notifications)

    @api.multi
    def _channel_message_notifications(self, message):
        """ Generate the bus notifications for the given message
            :param message : the mail.message to sent
            :returns list of bus notifications (tuple (bus_channe, message_content))
        """
        message_values = message.message_format()[0]
        notifications = []
        for channel in self:
            message_values['channel_ids'] = [channel.id]
            notifications.append([(self._cr.dbname, 'mail.channel', channel.id), dict(message_values)])
            # add uuid to allow anonymous to listen
            if channel.public == 'public':
                notifications.append([channel.uuid, dict(message_values)])
        return notifications

    @api.multi
    def channel_info(self, extra_info = False):
        """ Get the informations header for the current channels
            :returns a list of channels values
            :rtype : list(dict)
        """
        channel_infos = []
        partner_channels = self.env['mail.channel.partner']
        # find the channel partner state, if logged user
        if self.env.user and self.env.user.partner_id:
            partner_channels = self.env['mail.channel.partner'].search([('partner_id', '=', self.env.user.partner_id.id), ('channel_id', 'in', self.ids)])
        # for each channel, build the information header and include the logged partner information
        for channel in self:
            info = {
                'id': channel.id,
                'name': channel.name,
                'uuid': channel.uuid,
                'state': 'open',
                'is_minimized': False,
                'channel_type': channel.channel_type,
                'public': channel.public,
            }
            if extra_info:
                info['info'] = extra_info
            # add the partner for 'direct mesage' channel
            if channel.channel_type == 'chat':
                info['direct_partner'] = channel.sudo().channel_partner_ids.filtered(lambda p: p.id != self.env.user.partner_id.id).read(['id', 'name', 'im_status'])
            # add user session state, if available and if user is logged
            if partner_channels.ids:
                partner_channel = partner_channels.filtered(lambda c: channel.id == c.channel_id.id)
                if len(partner_channel) >= 1:
                    partner_channel = partner_channel[0]
                    info['state'] = partner_channel.fold_state or 'open'
                    info['is_minimized'] = partner_channel.is_minimized
                    info['seen_message_id'] = partner_channel.seen_message_id.id
                # add needaction and unread counter, since the user is logged
                info['message_needaction_counter'] = channel.message_needaction_counter
                info['message_unread_counter'] = channel.message_unread_counter
            channel_infos.append(info)
        return channel_infos

    @api.multi
    def channel_fetch_message(self, last_id=False, limit=20):
        """ Return message values of the current channel.
            :param last_id : last message id to start the research
            :param limit : maximum number of messages to fetch
            :returns list of messages values
            :rtype : list(dict)
        """
        self.ensure_one()
        domain = [("channel_ids", "in", self.ids)]
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
            :returns a channel header, or False if the users_to was False
            :rtype : dict
        """
        if partners_to:
            partners_to.append(self.env.user.partner_id.id)
            # determine type according to the number of partner in the channel
            self.env.cr.execute("""
                SELECT P.channel_id as channel_id
                FROM mail_channel C, mail_channel_partner P
                WHERE P.channel_id = C.id
                    AND C.public LIKE 'private'
                    AND P.partner_id IN %s
                    AND channel_type LIKE 'chat'
                GROUP BY P.channel_id
                HAVING COUNT(P.partner_id) = %s
            """, (tuple(partners_to), len(partners_to),))
            result = self.env.cr.dictfetchall()
            if result:
                # get the existing channel between the given partners
                channel = self.browse(result[0].get('channel_id'))
                # pin up the channel for the current partner
                if pin:
                    self.env['mail.channel.partner'].search([('partner_id', '=', self.env.user.partner_id.id), ('channel_id', '=', channel.id)]).write({'is_pinned': True})
            else:
                # create a new one
                channel = self.create({
                    'channel_partner_ids': [(4, partner_id) for partner_id in partners_to],
                    'public': 'private',
                    'channel_type': 'chat',
                    'email_send': False,
                    'name': ', '.join(self.env['res.partner'].sudo().browse(partners_to).mapped('name')),
                })
                # broadcast the channel header to the other partner (not me)
                channel._broadcast(partners_to)
            return channel.channel_info()[0]
        return False

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
        channel_partners = self.env['mail.channel.partner'].search(domain)
        channel_partners.write(values)
        self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner', self.env.user.partner_id.id), channel_partners.channel_id.channel_info()[0])

    @api.model
    def channel_pin(self, uuid, pinned=False):
        # add the person in the channel, and pin it (or unpin it)
        channel = self.search([('uuid', '=', uuid)])
        channel_partners = self.env['mail.channel.partner'].search([('partner_id', '=', self.env.user.partner_id.id), ('channel_id', '=', channel.id)])
        if not pinned:
            self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner', self.env.user.partner_id.id), channel.channel_info('unsubscribe')[0])
        if channel_partners:
            channel_partners.write({'is_pinned': pinned})

    @api.multi
    def channel_seen(self):
        self.ensure_one()
        if self.channel_message_ids.ids:
            last_message_id = self.channel_message_ids.ids[0] # zero is the index of the last message
            self.env['mail.channel.partner'].search([('channel_id', 'in', self.ids), ('partner_id', '=', self.env.user.partner_id.id)]).write({'seen_message_id': last_message_id})
            return last_message_id

    @api.multi
    def channel_invite(self, partner_ids):
        """ Add the given partner_ids to the current channels and broadcast the channel header to them.
            :param partner_ids : list of partner id to add
        """
        partners = self.env['res.partner'].browse(partner_ids)
        # add the partner
        for channel in self:
            partners_to_add = partners - channel.channel_partner_ids
            channel.write({'channel_last_seen_partner_ids': [(0, 0, {'partner_id': partner_id}) for partner_id in partners_to_add.ids]})
        # broadcast the channel header to the added partner
        self._broadcast(partner_ids)

    #------------------------------------------------------
    # Instant Messaging View Specific (Slack Client Action)
    #------------------------------------------------------
    @api.model
    def get_init_notifications(self):
        """ Get unread messages and old messages received less than AWAY_TIMER
            ago of minimized channel ONLY. This aims to set the minimized channel
            when refreshing the page.
            Note : the user need to be logged
        """
        # get current user's minimzed channel
        minimized_channels = self.env['mail.channel.partner'].search([('is_minimized', '=', True), ('partner_id', '=', self.env.user.partner_id.id)]).mapped('channel_id')

        # get the message since the AWAY_TIMER
        threshold = datetime.datetime.now() - datetime.timedelta(seconds=AWAY_TIMER)
        threshold = threshold.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        domain = [('channel_ids', 'in', minimized_channels.ids), ('create_date', '>', threshold)]

        # get the message since the last poll of the user
        presence = self.env['bus.presence'].search([('user_id', '=', self._uid)], limit=1)
        if presence:
            domain.append(('create_date', '>', presence.last_poll))

        # do the message search
        message_values = self.env['mail.message'].message_fetch(domain=domain)

        # create the notifications (channel infos first, then messages)
        notifications = []
        for channel_info in minimized_channels.channel_info():
            notifications.append([(self._cr.dbname, 'res.partner', self.env.user.partner_id.id), channel_info])
        for message_value in message_values:
            for channel_id in message_value['channel_ids']:
                if channel_id in minimized_channels.ids:
                    message_value['channel_ids'] = [channel_id]
                    notifications.append([(self._cr.dbname, 'mail.channel', channel_id), dict(message_value)])
        return notifications

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

        # get the partner of the pinned 'direct message' channels with mapping partner/channel
        direct_channel_partner = direct_message_channels.mapped('channel_last_seen_partner_ids').filtered(lambda cp: cp.partner_id.id != my_partner_id)
        values['mapping'] = dict((item.partner_id.id, item.channel_id.id) for item in direct_channel_partner)
        # partners of the 'direct message' channels
        values['partners'] = direct_message_channels.mapped('channel_partner_ids').filtered(lambda partner: partner.id != my_partner_id).read(['id', 'name', 'im_status'])

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
        domain += [('channel_type', '=', 'channel'), ('channel_partner_ids', 'not in', [self.env.user.partner_id.id])]
        if name:
            domain.append(('name', 'ilike', '%'+name+'%'))
        return self.search(domain).read(['name', 'public', 'uuid', 'channel_type'])

    @api.multi
    def channel_join_and_get_info(self):
        self.ensure_one()
        notification = _('<div class="o_mail_notification">joined <a href="#" class="o_channel_redirect" data-oe-id="%s">#%s</a></div>') % (self.id, self.name,)
        self.message_post(body=notification, message_type="notification", subtype="mail.mt_comment")
        self.action_follow()

        channel_info = self.channel_info()[0]
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
            'email_send': False,
            'channel_partner_ids': [(4, self.env.user.partner_id.id)]
        })
        channel_info = new_channel.channel_info()[0]
        notification = _('<div class="o_mail_notification">created <a href="#" class="o_channel_redirect" data-oe-id="%s">#%s</a></div>') % (new_channel.id, new_channel.name,)
        new_channel.message_post(body=notification, message_type="notification", subtype="mail.mt_comment")
        self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner', self.env.user.partner_id.id), channel_info)
        return channel_info

    @api.model
    def get_mention_suggestions(self, search, limit=8):
        """ Return 'limit'-first channels' id, name and public fields such that the name matches a
            'search' string. Exclude channels of type chat (DM), and private channels the current
            user isn't registered to. """
        domain = expression.AND([
                        [('name', 'ilike', search)],
                        [('channel_type', '!=', 'chat')],
                        expression.OR([
                            [('public', '!=', 'private')],
                            [('channel_partner_ids', 'in', [self.env.user.partner_id.id])]
                        ])
                    ])
        return self.search_read(domain, ['id', 'name', 'public'], limit=limit)
