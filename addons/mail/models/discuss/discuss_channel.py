# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from collections import defaultdict
from hashlib import sha512
from secrets import choice
from markupsafe import Markup
from datetime import timedelta

from odoo import _, api, fields, models, tools, Command
from odoo.addons.base.models.avatar_mixin import get_hsl_from_seed
from odoo.addons.mail.tools.discuss import Store
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.osv import expression
from odoo.tools import format_list, get_lang, html_escape

channel_avatar = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 530.06 530.06">
<circle cx="265.03" cy="265.03" r="265.03" fill="#875a7b"/>
<path d="M416.74,217.29l5-28a8.4,8.4,0,0,0-8.27-9.88H361.09l10.24-57.34a8.4,8.4,0,0,0-8.27-9.88H334.61a8.4,8.4,0,0,0-8.27,6.93L315.57,179.4H246.5l10.24-57.34a8.4,8.4,0,0,0-8.27-9.88H220a8.4,8.4,0,0,0-8.27,6.93L201,179.4H145.6a8.42,8.42,0,0,0-8.28,6.93l-5,28a8.4,8.4,0,0,0,8.27,9.88H193l-16,89.62H121.59a8.4,8.4,0,0,0-8.27,6.93l-5,28a8.4,8.4,0,0,0,8.27,9.88H169L158.73,416a8.4,8.4,0,0,0,8.27,9.88h28.45a8.42,8.42,0,0,0,8.28-6.93l10.76-60.29h69.07L273.32,416a8.4,8.4,0,0,0,8.27,9.88H310a8.4,8.4,0,0,0,8.27-6.93l10.77-60.29h55.38a8.41,8.41,0,0,0,8.28-6.93l5-28a8.4,8.4,0,0,0-8.27-9.88H337.08l16-89.62h55.38A8.4,8.4,0,0,0,416.74,217.29ZM291.56,313.84H222.5l16-89.62h69.07Z" fill="#ffffff"/>
</svg>'''
group_avatar = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 530.06 530.06">
<circle cx="265.03" cy="265.03" r="265.03" fill="#875a7b"/>
<path d="m184.356059,265.030004c-23.740561,0.73266 -43.157922,10.11172 -58.252302,28.136961l-29.455881,0c-12.0169,0 -22.128621,-2.96757 -30.335161,-8.90271s-12.309921,-14.618031 -12.309921,-26.048671c0,-51.730902 9.08582,-77.596463 27.257681,-77.596463c0.87928,0 4.06667,1.53874 9.56217,4.61622s12.639651,6.19167 21.432451,9.34235s17.512401,4.72613 26.158581,4.72613c9.8187,0 19.563981,-1.68536 29.236061,-5.05586c-0.73266,5.4223 -1.0991,10.25834 -1.0991,14.508121c0,20.370061 5.93514,39.127962 17.805421,56.273922zm235.42723,140.025346c0,17.585601 -5.34888,31.470971 -16.046861,41.655892s-24.912861,15.277491 -42.645082,15.277491l-192.122688,0c-17.732221,0 -31.947101,-5.09257 -42.645082,-15.277491s-16.046861,-24.070291 -16.046861,-41.655892c0,-7.7669 0.25653,-15.350691 0.76937,-22.751371s1.53874,-15.387401 3.07748,-23.960381s3.48041,-16.523211 5.82523,-23.850471s5.4955,-14.471411 9.45226,-21.432451s8.49978,-12.89618 13.628841,-17.805421c5.12906,-4.90924 11.393931,-8.82951 18.794611,-11.76037s15.570511,-4.3964 24.509931,-4.3964c1.46554,0 4.61622,1.57545 9.45226,4.72613s10.18492,6.6678 16.046861,10.55136c5.86194,3.88356 13.702041,7.40068 23.520741,10.55136s19.710601,4.72613 29.675701,4.72613s19.857001,-1.57545 29.675701,-4.72613s17.658801,-6.6678 23.520741,-10.55136c5.86194,-3.88356 11.21082,-7.40068 16.046861,-10.55136s7.98672,-4.72613 9.45226,-4.72613c8.93942,0 17.109251,1.46554 24.509931,4.3964s13.665551,6.85113 18.794611,11.76037c5.12906,4.90924 9.67208,10.844381 13.628841,17.805421s7.10744,14.105191 9.45226,21.432451s4.28649,15.277491 5.82523,23.850471s2.56464,16.559701 3.07748,23.960381s0.76937,14.984471 0.76937,22.751371zm-225.095689,-280.710152c0,15.534021 -5.4955,28.796421 -16.486501,39.787422s-24.253401,16.486501 -39.787422,16.486501s-28.796421,-5.4955 -39.787422,-16.486501s-16.486501,-24.253401 -16.486501,-39.787422s5.4955,-28.796421 16.486501,-39.787422s24.253401,-16.486501 39.787422,-16.486501s28.796421,5.4955 39.787422,16.486501s16.486501,24.253401 16.486501,39.787422zm154.753287,84.410884c0,23.300921 -8.24325,43.194632 -24.729751,59.681133s-36.380212,24.729751 -59.681133,24.729751s-43.194632,-8.24325 -59.681133,-24.729751s-24.729751,-36.380212 -24.729751,-59.681133s8.24325,-43.194632 24.729751,-59.681133s36.380212,-24.729751 59.681133,-24.729751s43.194632,8.24325 59.681133,24.729751s24.729751,36.380212 24.729751,59.681133zm126.616325,49.459502c0,11.43064 -4.10338,20.113531 -12.309921,26.048671s-18.318261,8.90271 -30.335161,8.90271l-29.455881,0c-15.094381,-18.025241 -34.511741,-27.404301 -58.252302,-28.136961c11.87028,-17.145961 17.805421,-35.903862 17.805421,-56.273922c0,-4.24978 -0.36644,-9.08582 -1.0991,-14.508121c9.67208,3.3705 19.417361,5.05586 29.236061,5.05586c8.64618,0 17.365781,-1.57545 26.158581,-4.72613s15.936951,-6.26487 21.432451,-9.34235s8.68289,-4.61622 9.56217,-4.61622c18.171861,0 27.257681,25.865561 27.257681,77.596463zm-28.136961,-133.870386c0,15.534021 -5.4955,28.796421 -16.486501,39.787422s-24.253401,16.486501 -39.787422,16.486501s-28.796421,-5.4955 -39.787422,-16.486501s-16.486501,-24.253401 -16.486501,-39.787422s5.4955,-28.796421 16.486501,-39.787422s24.253401,-16.486501 39.787422,-16.486501s28.796421,5.4955 39.787422,16.486501s16.486501,24.253401 16.486501,39.787422z" fill="#ffffff"/>
</svg>'''


class Channel(models.Model):
    _description = 'Discussion Channel'
    _name = 'discuss.channel'
    _mail_flat_thread = False
    _mail_post_access = 'read'
    _inherit = ['mail.thread']

    MAX_BOUNCE_LIMIT = 10

    @api.model
    def _generate_random_token(self):
        # Built to be shared on invitation link. It uses non-ambiguous characters and it is of a
        # reasonable length: enough to avoid brute force, but short enough to be shareable easily.
        # This token should not contain "mail.guest"._cookie_separator value.
        return ''.join(choice('abcdefghijkmnopqrstuvwxyzABCDEFGHIJKLMNPQRSTUVWXYZ23456789') for _i in range(10))

    # description
    name = fields.Char('Name', required=True)
    active = fields.Boolean(default=True, help="Set active to false to hide the channel without removing it.")
    channel_type = fields.Selection([
        ('chat', 'Chat'),
        ('channel', 'Channel'),
        ('group', 'Group')],
        string='Channel Type', required=True, default='channel', readonly=True, help="Chat is private and unique between 2 persons. Group is private among invited persons. Channel can be freely joined (depending on its configuration).")
    is_editable = fields.Boolean('Is Editable', compute='_compute_is_editable')
    default_display_mode = fields.Selection(string="Default Display Mode", selection=[('video_full_screen', "Full screen video")], help="Determines how the channel will be displayed by default when opening it from its invitation link. No value means display text (no voice/video).")
    description = fields.Text('Description')
    image_128 = fields.Image("Image", max_width=128, max_height=128)
    avatar_128 = fields.Image("Avatar", max_width=128, max_height=128, compute='_compute_avatar_128')
    avatar_cache_key = fields.Char(compute="_compute_avatar_cache_key")
    channel_partner_ids = fields.Many2many(
        'res.partner', string='Partners',
        compute='_compute_channel_partner_ids', inverse='_inverse_channel_partner_ids',
        search='_search_channel_partner_ids')
    channel_member_ids = fields.One2many('discuss.channel.member', 'channel_id', string='Members')
    pinned_message_ids = fields.One2many('mail.message', 'res_id', domain=[('model', '=', 'discuss.channel'), ('pinned_at', '!=', False)], string='Pinned Messages')
    sfu_channel_uuid = fields.Char(groups="base.group_system")
    sfu_server_url = fields.Char(groups="base.group_system")
    rtc_session_ids = fields.One2many('discuss.channel.rtc.session', 'channel_id', groups="base.group_system")
    is_member = fields.Boolean('Is Member', compute='_compute_is_member', search='_search_is_member')
    member_count = fields.Integer(string="Member Count", compute='_compute_member_count', compute_sudo=True)
    last_interest_dt = fields.Datetime("Last Interest", index=True, help="Contains the date and time of the last interesting event that happened in this channel. This updates itself when new message posted.")
    group_ids = fields.Many2many(
        'res.groups', string='Auto Subscription',
        help="Members of those groups will automatically added as followers. "
             "Note that they will be able to manage their subscription manually "
             "if necessary.")
    # access
    uuid = fields.Char('UUID', size=50, default=_generate_random_token, copy=False)
    group_public_id = fields.Many2one('res.groups', string='Authorized Group', compute='_compute_group_public_id', readonly=False, store=True)
    invitation_url = fields.Char('Invitation URL', compute='_compute_invitation_url')
    allow_public_upload = fields.Boolean(default=False)
    _sql_constraints = [
        ('channel_type_not_null', 'CHECK(channel_type IS NOT NULL)', 'The channel type cannot be empty'),
        ('uuid_unique', 'UNIQUE(uuid)', 'The channel UUID must be unique'),
        ('group_public_id_check',
         "CHECK (channel_type = 'channel' OR group_public_id IS NULL)",
         'Group authorization and group auto-subscription are only supported on channels.')
    ]

    # CONSTRAINTS

    @api.constrains('channel_member_ids')
    def _constraint_partners_chat(self):
        # sudo: discuss.channel - skipping ACL for constraint, more performant and no sensitive information is leaked
        for ch in self.sudo().filtered(lambda ch: ch.channel_type == 'chat'):
            if len(ch.channel_member_ids) > 2:
                raise ValidationError(_("A channel of type 'chat' cannot have more than two users."))

    @api.constrains('group_public_id', 'group_ids')
    def _constraint_group_id_channel(self):
        # sudo: discuss.channel - skipping ACL for constraint, more performant and no sensitive information is leaked
        failing_channels = self.sudo().filtered(lambda channel: channel.channel_type != 'channel' and (channel.group_public_id or channel.group_ids))
        if failing_channels:
            raise ValidationError(_("For %(channels)s, channel_type should be 'channel' to have the group-based authorization or group auto-subscription.", channels=', '.join([ch.name for ch in failing_channels])))

    # COMPUTE / INVERSE

    @api.depends("channel_type", "is_member", "group_public_id")
    @api.depends_context("uid")
    def _compute_is_editable(self):
        if not self.check_access_rights("write", raise_exception=False):
            self.is_editable = False
            return
        for channel in self:
            try:
                channel.check_access_rule("write")
                channel.is_editable = True
            except AccessError:
                channel.is_editable = False

    @api.depends('channel_type', 'image_128', 'uuid')
    def _compute_avatar_128(self):
        for record in self:
            record.avatar_128 = record.image_128 or record._generate_avatar()

    @api.depends('avatar_128')
    def _compute_avatar_cache_key(self):
        for channel in self:
            if not channel.avatar_128:
                channel.avatar_cache_key = 'no-avatar'
            else:
                channel.avatar_cache_key = sha512(channel.avatar_128).hexdigest()

    def _generate_avatar(self):
        if self.channel_type not in ('channel', 'group'):
            return False
        avatar = group_avatar if self.channel_type == 'group' else channel_avatar
        bgcolor = get_hsl_from_seed(self.uuid)
        avatar = avatar.replace('fill="#875a7b"', f'fill="{bgcolor}"')
        return base64.b64encode(avatar.encode())

    @api.depends('channel_member_ids.partner_id')
    def _compute_channel_partner_ids(self):
        for channel in self:
            channel.channel_partner_ids = channel.channel_member_ids.partner_id

    def _inverse_channel_partner_ids(self):
        new_members = []
        outdated = self.env['discuss.channel.member']
        for channel in self:
            current_members = channel.channel_member_ids
            partners = channel.channel_partner_ids
            partners_new = partners - current_members.partner_id

            new_members += [{
                'channel_id': channel.id,
                'partner_id': partner.id,
            } for partner in partners_new]
            outdated += current_members.filtered(lambda m: m.partner_id not in partners)
        if new_members:
            self.env['discuss.channel.member'].create(new_members)
        if outdated:
            outdated.unlink()

    def _search_channel_partner_ids(self, operator, operand):
        return [('channel_member_ids', 'any', [('partner_id', operator, operand)])]

    @api.depends_context('uid', 'guest')
    @api.depends('channel_member_ids')
    def _compute_is_member(self):
        if not self:
            return
        members = self.env['discuss.channel.member'].search([('channel_id', 'in', self.ids), ('is_self', '=', True)])
        is_member_channels = members.channel_id
        for channel in self:
            channel.is_member = channel in is_member_channels

    def _search_is_member(self, operator, operand):
        is_in = (operator == '=' and operand) or (operator == '!=' and not operand)
        # Separate query to fetch candidate channels because the sub-select that _search would
        # generate leads psql query plan to take bad decisions. When candidate ids are explicitly
        # given it doesn't need to make (incorrect) guess, at the cost of one extra but fast query.
        # It is expected to return hundreds of channels, a thousand at most, which is acceptable.
        # A "join" would be ideal, but the ORM is currently not able to generate it from the domain.
        current_partner, current_guest = self.env["res.partner"]._get_current_persona()
        if current_guest:
            # sudo: discuss.channel - sudo for performance, just checking existence
            channels = current_guest.sudo().channel_ids
        elif current_partner:
            # sudo: discuss.channel - sudo for performance, just checking existence
            channels = current_partner.sudo().channel_ids
        else:
            channels = self.env["discuss.channel"]
        return [('id', "in" if is_in else "not in", channels.ids)]

    @api.depends('channel_member_ids')
    def _compute_member_count(self):
        read_group_res = self.env['discuss.channel.member']._read_group(domain=[('channel_id', 'in', self.ids)], groupby=['channel_id'], aggregates=['__count'])
        member_count_by_channel_id = {channel.id: count for channel, count in read_group_res}
        for channel in self:
            channel.member_count = member_count_by_channel_id.get(channel.id, 0)

    @api.depends('channel_type')
    def _compute_group_public_id(self):
        channels = self.filtered(lambda channel: channel.channel_type == 'channel')
        channels.filtered(lambda channel: not channel.group_public_id).group_public_id = self.env.ref('base.group_user')
        (self - channels).group_public_id = None

    @api.depends('uuid')
    def _compute_invitation_url(self):
        for channel in self:
            channel.invitation_url = f"/chat/{channel.id}/{channel.uuid}"

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # find partners to add from partner_ids
            partner_ids_cmd = vals.get('channel_partner_ids') or []
            if any(cmd[0] not in (4, 6) for cmd in partner_ids_cmd):
                raise ValidationError(_('Invalid value when creating a channel with members, only 4 or 6 are allowed.'))
            partner_ids = [cmd[1] for cmd in partner_ids_cmd if cmd[0] == 4]
            partner_ids += [cmd[2] for cmd in partner_ids_cmd if cmd[0] == 6]

            # find partners to add from channel_member_ids
            membership_ids_cmd = vals.get('channel_member_ids', [])
            for cmd in membership_ids_cmd:
                if cmd[0] != 0:
                    raise ValidationError(_('Invalid value when creating a channel with memberships, only 0 is allowed.'))
                for field_name in cmd[2]:
                    if field_name not in ["partner_id", "guest_id", "unpin_dt", "last_interest_dt", "fold_state"]:
                        raise ValidationError(
                            _(
                                "Invalid field “%(field_name)s” when creating a channel with members.",
                                field_name=field_name,
                            )
                        )
            membership_pids = [cmd[2]['partner_id'] for cmd in membership_ids_cmd if cmd[0] == 0]

            partner_ids_to_add = partner_ids
            # always add current user to new channel to have right values for
            # is_pinned + ensure they have rights to see channel
            if not self.env.context.get('install_mode') and not self.env.user._is_public():
                partner_ids_to_add = list(set(partner_ids + [self.env.user.partner_id.id]))
            vals['channel_member_ids'] = membership_ids_cmd + [
                (0, 0, {'partner_id': pid})
                for pid in partner_ids_to_add if pid not in membership_pids
            ]

            # clean vals
            vals.pop('channel_partner_ids', False)

        # Create channel and alias
        channels = super(Channel, self.with_context(mail_create_bypass_create_check=self.env['discuss.channel.member']._bypass_create_check, mail_create_nolog=True, mail_create_nosubscribe=True)).create(vals_list)
        # pop the mail_create_bypass_create_check key to avoid leaking it outside of create)
        channels = channels.with_context(mail_create_bypass_create_check=None)
        channels._subscribe_users_automatically()

        return channels

    @api.ondelete(at_uninstall=False)
    def _unlink_except_all_employee_channel(self):
        # Delete discuss.channel
        try:
            all_emp_group = self.env.ref('mail.channel_all_employees')
        except ValueError:
            all_emp_group = None
        if all_emp_group and all_emp_group in self:
            raise UserError(_('You cannot delete those groups, as the Whole Company group is required by other modules.'))
        self.env['bus.bus']._sendmany([(channel, 'discuss.channel/delete', {'id': channel.id}) for channel in self])

    def write(self, vals):
        if 'channel_type' in vals:
            failing_channels = self.filtered(lambda channel: channel.channel_type != vals.get('channel_type'))
            if failing_channels:
                raise UserError(_('Cannot change the channel type of: %(channel_names)s', channel_names=', '.join(failing_channels.mapped('name'))))
        old_vals = {channel: channel._channel_basic_info() for channel in self}
        result = super().write(vals)
        notifications = []
        for channel in self:
            info = channel._channel_basic_info()
            diff = {}
            for key, value in info.items():
                if value != old_vals[channel][key]:
                    diff[key] = value
            if diff:
                notifications.append([channel, "mail.record/insert", {
                    "Thread": {
                        "id": channel.id,
                        "model": "discuss.channel",
                        **diff
                    }
                }])
        if vals.get('group_ids'):
            self._subscribe_users_automatically()
        self.env['bus.bus']._sendmany(notifications)
        return result

    def init(self):
        self._cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('discuss_channel_member_seen_message_id_idx',))
        if not self._cr.fetchone():
            self._cr.execute('CREATE INDEX discuss_channel_member_seen_message_id_idx ON discuss_channel_member (channel_id,partner_id,seen_message_id)')

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
            # sudo: discuss.channel.member - adding member of other users based on channel auto-subscribe
            self.env['discuss.channel.member'].sudo().create(to_create)
        notifications = []
        for channel in self:
            for group in channel.group_ids:
                notifications.append((group, 'mail.record/insert', {
                    'Thread': {
                        **channel._channel_basic_info(),
                        "is_pinned": True,
                    }
                }))
        self.env["bus.bus"]._sendmany(notifications)

    def _subscribe_users_automatically_get_members(self):
        """ Return new members per channel ID """
        return dict(
            (channel.id,
             ((channel.group_ids.users.partner_id.filtered(lambda p: p.active) - channel.channel_partner_ids).ids))
                for channel in self
            )

    def action_unfollow(self):
        self._action_unfollow(self.env.user.partner_id)

    def _action_unfollow(self, partner):
        self.message_unsubscribe(partner.ids)
        custom_channel_info = {
            "id": self.id,
            "is_pinned": False,
            "isLocallyPinned": False,
            "model": "discuss.channel",
        }
        custom_store = Store("Thread", custom_channel_info)
        member = self.env["discuss.channel.member"].search(
            [("channel_id", "=", self.id), ("partner_id", "=", partner.id)]
        )
        if not member:
            self.env["bus.bus"]._sendone(partner, "discuss.channel/leave", custom_store.get_result())
            return
        member.unlink()
        notification = Markup('<div class="o_mail_notification">%s</div>') % _("left the channel")
        # sudo: mail.message - post as sudo since the user just unsubscribed from the channel
        self.sudo().message_post(
            body=notification, subtype_xmlid="mail.mt_comment", author_id=partner.id
        )
        # send custom store after message_post to avoid is_pinned reset to True
        self.env["bus.bus"]._sendone(partner, "discuss.channel/leave", custom_store.get_result())
        channel_info = {
            "channelMembers": [("DELETE", {"id": member.id})],
            "id": self.id,
            "memberCount": self.member_count,
            "model": "discuss.channel",
        }
        store = Store("Thread", channel_info)
        self.env["bus.bus"]._sendone(self, "mail.record/insert", store.get_result())

    def add_members(self, partner_ids=None, guest_ids=None, invite_to_rtc_call=False, open_chat_window=False, post_joined_message=True):
        """ Adds the given partner_ids and guest_ids as member of self channels. """
        current_partner, current_guest = self.env["res.partner"]._get_current_persona()
        partners = self.env['res.partner'].browse(partner_ids or []).exists()
        guests = self.env['mail.guest'].browse(guest_ids or []).exists()
        notifications = []
        all_new_members = self.env["discuss.channel.member"]
        for channel in self:
            members_to_create = []
            existing_members = self.env['discuss.channel.member'].search(expression.AND([
                [('channel_id', '=', channel.id)],
                expression.OR([
                    [('partner_id', 'in', partners.ids)],
                    [('guest_id', 'in', guests.ids)]
                ])
            ]))
            members_to_create += [{
                'partner_id': partner.id,
                'channel_id': channel.id,
            } for partner in partners - existing_members.partner_id]
            members_to_create += [{
                'guest_id': guest.id,
                'channel_id': channel.id,
            } for guest in guests - existing_members.guest_id]
            new_members = self.env['discuss.channel.member'].create(members_to_create)
            all_new_members += new_members
            for member in new_members.filtered(lambda member: member.partner_id):
                # notify invited members through the bus
                user = member.partner_id.user_ids[0] if member.partner_id.user_ids else self.env['res.users']
                if user:
                    notifications.append((member.partner_id, 'discuss.channel/joined', {
                        'channel': {
                            **member.channel_id._channel_basic_info(),
                            "is_pinned": True,
                        },
                        'invited_by_user_id': self.env.user.id,
                        'open_chat_window': open_chat_window,
                    }))
                if post_joined_message:
                    # notify existing members with a new message in the channel
                    if member.partner_id == self.env.user.partner_id:
                        notification = Markup('<div class="o_mail_notification">%s</div>') % _('joined the channel')
                    else:
                        notification = (Markup('<div class="o_mail_notification">%s</div>') % _("invited %s to the channel")) % member.partner_id._get_html_link()
                    member.channel_id.message_post(body=notification, message_type="notification", subtype_xmlid="mail.mt_comment")
            for member in new_members.filtered(lambda member: member.guest_id):
                if post_joined_message:
                    member.channel_id.message_post(body=Markup('<div class="o_mail_notification">%s</div>') % _('joined the channel'),
                        message_type="notification", subtype_xmlid="mail.mt_comment")
                guest = member.guest_id
                if guest:
                    notifications.append((guest, 'discuss.channel/joined', {
                        'channel': member.channel_id._channel_basic_info(),
                    }))
            if new_members:
                store = Store(
                    "Thread",
                    {
                        "id": channel.id,
                        "memberCount": channel.member_count,
                        "model": "discuss.channel",
                    },
                )
                store.add(new_members)
                notifications.append((channel, "mail.record/insert", store.get_result()))
            if existing_members and (current_partner or current_guest):
                # If the current user invited these members but they are already present, notify the current user about their existence as well.
                # In particular this fixes issues where the current user is not aware of its own member in the following case:
                # create channel from form view, and then join from discuss without refreshing the page.
                user_store = Store(
                    "Thread",
                    {
                        "id": channel.id,
                        "memberCount": channel.member_count,
                        "model": "discuss.channel",
                    },
                )
                user_store.add(existing_members)
                target = current_partner or current_guest
                notifications.append((target, "mail.record/insert", user_store.get_result()))
        if invite_to_rtc_call:
            for channel in self:
                current_channel_member = self.env['discuss.channel.member'].search([('channel_id', '=', channel.id), ('is_self', '=', True)])
                # sudo: discuss.channel.rtc.session - reading rtc sessions of current user
                if current_channel_member and current_channel_member.sudo().rtc_session_ids:
                    # sudo: discuss.channel.rtc.session - current user can invite new members in call
                    current_channel_member.sudo()._rtc_invite_members(member_ids=new_members.ids)
        self.env['bus.bus']._sendmany(notifications)
        return all_new_members

    # ------------------------------------------------------------
    # RTC
    # ------------------------------------------------------------

    def _rtc_cancel_invitations(self, member_ids=None):
        """ Cancels the invitations of the RTC call from all invited members,
            if member_ids is provided, only the invitations of the specified members are canceled.

            :param list member_ids: list of the members ids from which the invitation has to be removed
        """
        self.ensure_one()
        channel_member_domain = [
            ('channel_id', '=', self.id),
            ('rtc_inviting_session_id', '!=', False),
        ]
        if member_ids:
            channel_member_domain = expression.AND([channel_member_domain, [('id', 'in', member_ids)]])
        notifications = []
        members = self.env['discuss.channel.member'].search(channel_member_domain)
        for member in members:
            member.rtc_inviting_session_id = False
            target = member.partner_id or member.guest_id
            store = Store(
                "Thread",
                {
                    "id": self.id,
                    "model": "discuss.channel",
                    "rtcInvitingSession": False,
                }
            )
            notifications.append((target, "mail.record/insert", store.get_result()))
        if members:
            store = Store(
                "Thread",
                {
                    "id": self.id,
                    "model": "discuss.channel",
                    "invitedMembers": [("DELETE", [{"id": member.id} for member in members])],
                },
            )
            store.add(
                members,
                fields={
                    "id": True,
                    "channel": {},
                    "persona": {
                        "partner": {"id": True, "name": True, "im_status": True},
                        "guest": {"id": True, "name": True, "im_status": True},
                    },
                },
            )
            notifications.append((self, "mail.record/insert", store.get_result()))
        self.env["bus.bus"]._sendmany(notifications)

    # ------------------------------------------------------------
    # MAILING
    # ------------------------------------------------------------

    def _notify_get_recipients(self, message, msg_vals, **kwargs):
        """ Override recipients computation as channel is not a standard
        mail.thread document. Indeed there are no followers on a channel.
        Instead of followers it has members that should be notified.

        :param message: see ``MailThread._notify_get_recipients()``;
        :param msg_vals: see ``MailThread._notify_get_recipients()``;
        :param kwargs: see ``MailThread._notify_get_recipients()``;

        :return recipients: structured data holding recipients data. See
          ``MailThread._notify_thread()`` for more details about its content
          and use;
        """
        # get values from msg_vals or from message if msg_vals doen't exists
        message_type = msg_vals.get('message_type', 'comment') if msg_vals else message.message_type
        pids = msg_vals.get('partner_ids', []) if msg_vals else message.partner_ids.ids

        # notify only user input (comment, whatsapp messages or incoming / outgoing emails)
        if message_type not in ('comment', 'email', 'email_outgoing', 'whatsapp_message'):
            return []

        recipients_data = []
        author_id = msg_vals.get("author_id") or message.author_id.id
        if pids:
            email_from = tools.email_normalize(msg_vals.get('email_from') or message.email_from)
            self.env['res.partner'].flush_model(['active', 'email', 'partner_share'])
            self.env['res.users'].flush_model(['notification_type', 'partner_id'])
            sql_query = """
                SELECT DISTINCT ON (partner.id) partner.id,
                       partner.lang,
                       partner.partner_share,
                       users.id as uid,
                       COALESCE(users.notification_type, 'email') as notif,
                       COALESCE(users.share, FALSE) as ushare
                  FROM res_partner partner
             LEFT JOIN res_users users on partner.id = users.partner_id
                 WHERE partner.active IS TRUE
                       AND partner.email != %s
                       AND partner.id = ANY(%s) AND partner.id != ANY(%s)"""
            self.env.cr.execute(
                sql_query,
                (email_from or '', list(pids), [author_id] if author_id else [], )
            )
            for partner_id, lang, partner_share, uid, notif, ushare in self._cr.fetchall():
                # ocn_client: will add partners to recipient recipient_data. more ocn notifications. We neeed to filter them maybe
                recipients_data.append({
                    'active': True,
                    'id': partner_id,
                    'is_follower': False,
                    'groups': [],
                    'lang': lang,
                    'notif': notif,
                    'share': partner_share,
                    'type': 'user' if not partner_share and notif else 'customer',
                    'uid': uid,
                    'ushare': ushare,
                })

        domain = expression.AND([
            [("channel_id", "=", self.id)],
            [("partner_id", "!=", author_id)],
            [("partner_id.active", "=", True)],
            [("mute_until_dt", "=", False)],
            [("partner_id.user_ids.res_users_settings_ids.mute_until_dt", "=", False)],
            expression.OR([
                [("channel_id.channel_type", "!=", "channel")],
                expression.AND([
                    [("channel_id.channel_type", "=", "channel")],
                    expression.OR([
                        [("custom_notifications", "=", "all")],
                        expression.AND([
                            [("custom_notifications", "=", False)],
                            [("partner_id.user_ids.res_users_settings_ids.channel_notifications", "=", "all")],
                        ]),
                        expression.AND([
                            [("custom_notifications", "=", "mentions")],
                            [("partner_id", "in", pids)],
                        ]),
                        expression.AND([
                            [("custom_notifications", "=", False)],
                            [("partner_id.user_ids.res_users_settings_ids.channel_notifications", "=", False)],
                            [("partner_id", "in", pids)],
                        ]),
                    ]),
                ]),
            ]),
        ])
        # sudo: discuss.channel.member - read to get the members of the channel and res.users.settings of the partners
        members = self.env["discuss.channel.member"].sudo().search(domain)
        for member in members:
            recipients_data.append({
                "active": True,
                "id": member.partner_id.id,
                "is_follower": False,
                "groups": [],
                "lang": member.partner_id.lang,
                "notif": "web_push",
                "share": member.partner_id.partner_share,
                "type": "customer",
                "uid": False,
                "ushare": False,
            })
        return recipients_data

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=None):
        """ All recipients of a message on a channel are considered as partners.
        This means they will receive a minimal email, without a link to access
        in the backend. Mailing lists should indeed send minimal emails to avoid
        the noise. """
        groups = super()._notify_get_recipients_groups(
            message, model_description, msg_vals=msg_vals
        )
        for (index, (group_name, _group_func, group_data)) in enumerate(groups):
            if group_name != 'customer':
                groups[index] = (group_name, lambda partner: False, group_data)
        return groups

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        # link message to channel
        rdata = super()._notify_thread(message, msg_vals=msg_vals, **kwargs)
        payload = {"data": Store(message).get_result(), "id": self.id}
        if temporary_id := self.env.context.get("temporary_id"):
            payload["temporary_id"] = temporary_id
        bus_notifications = [
            (
                (self, "members"),
                "mail.record/insert",
                {"Thread": {"id": self.id, "is_pinned": True, "model": "discuss.channel"}},
            ),
            (self, "discuss.channel/new_message", payload),
        ]
        # sudo: bus.bus - sending on safe channel (discuss.channel)
        self.env["bus.bus"].sudo()._sendmany(bus_notifications)
        return rdata

    def _notify_by_web_push_prepare_payload(self, message, msg_vals=False):
        payload = super()._notify_by_web_push_prepare_payload(message, msg_vals=msg_vals)
        payload['options']['data']['action'] = 'mail.action_discuss'
        record_name = msg_vals.get('record_name') if msg_vals and 'record_name' in msg_vals else message.record_name
        author_id = [msg_vals["author_id"]] if msg_vals and msg_vals.get("author_id") else message.author_id.ids
        author = self.env["res.partner"].browse(author_id) or self.env["mail.guest"].browse(
            msg_vals.get("author_guest_id", message.author_guest_id.id)
        )
        if self.channel_type == 'chat':
            payload['title'] = author.name
        elif self.channel_type == 'channel':
            payload['title'] = "#%s - %s" % (record_name, author.name)
        elif self.channel_type == 'group':
            if not record_name:
                member_names = self.channel_member_ids.mapped(lambda m: m.partner_id.name if m.partner_id else m.guest_id.name)
                record_name = f"{', '.join(member_names[:-1])} and {member_names[-1]}" if len(member_names) > 1 else member_names[0] if member_names else ""
            payload['title'] = "%s - %s" % (record_name, author.name)
        else:
            payload['title'] = "#%s" % (record_name)
        return payload

    def _notify_thread_by_web_push(self, message, recipients_data, msg_vals=False, **kwargs):
        # only notify "web_push" recipients in discuss channels.
        # exclude "inbox" recipients in discuss channels as inbox and web push can be mutually exclusive.
        # the user can turn off the web push but receive notifs via inbox if they want to.
        super()._notify_thread_by_web_push(message, [r for r in recipients_data if r["notif"] == "web_push"], msg_vals=msg_vals, **kwargs)

    def _message_receive_bounce(self, email, partner):
        """ Override bounce management to unsubscribe bouncing addresses """
        for p in partner:
            if p.message_bounce >= self.MAX_BOUNCE_LIMIT:
                self._action_unfollow(p)
        return super()._message_receive_bounce(email, partner)

    def _message_compute_author(self, author_id=None, email_from=None, raise_on_email=True):
        return super()._message_compute_author(author_id=author_id, email_from=email_from, raise_on_email=False)

    def _message_compute_parent_id(self, parent_id):
        # super() unravels the chain of parents to set parent_id as the first
        # ancestor. We don't want that in channel.
        if not parent_id:
            return parent_id
        return self.env['mail.message'].search(
            [('id', '=', parent_id),
             ('model', '=', self._name),
             ('res_id', '=', self.id)
            ]).id

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, *, message_type='notification', **kwargs):
        if (not self.env.user or self.env.user._is_public()) and self.is_member:
            # sudo: discuss.channel - guests don't have access for creating mail.message
            self = self.sudo()
        # sudo: discuss.channel - write to discuss.channel is not accessible for most users
        self.sudo().last_interest_dt = fields.Datetime.now()
        # mail_post_autofollow=False is necessary to prevent adding followers
        # when using mentions in channels. Followers should not be added to
        # channels, and especially not automatically (because channel membership
        # should be managed with discuss.channel.member instead).
        # The current client code might be setting the key to True on sending
        # message but it is only useful when targeting customers in chatter.
        # This value should simply be set to False in channels no matter what.
        return super(Channel, self.with_context(mail_create_nosubscribe=True, mail_post_autofollow=False)).message_post(message_type=message_type, **kwargs)

    def _message_post_after_hook(self, message, msg_vals):
        """
        Automatically set the message posted by the current user as seen for themselves.
        """
        if (current_channel_member := self.env["discuss.channel.member"].search([
            ("channel_id", "=", self.id), ("is_self", "=", True)
        ])) and message.is_current_user_or_guest_author:
            current_channel_member._set_last_seen_message(message, notify=False)
            current_channel_member._set_new_message_separator(message.id + 1, sync=True)
        return super()._message_post_after_hook(message, msg_vals)

    def _check_can_update_message_content(self, message):
        """ We don't call super in this override as we want to ignore the
        mail.thread behavior completely """
        if not message.message_type == 'comment':
            raise UserError(_("Only messages type comment can have their content updated on model 'discuss.channel'"))

    def _create_attachments_for_post(self, values_list, extra_list):
        # Create voice metadata from meta information
        attachments = super()._create_attachments_for_post(values_list, extra_list)
        voice = attachments.env['ir.attachment']  # keep env, notably for potential sudo
        for attachment, (_cid, _name, _token, info) in zip(attachments, extra_list):
            if info.get('voice'):
                voice += attachment
        if voice:
            voice._set_voice_metadata()
        return attachments

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
        self.env['bus.bus']._sendmany(notifications)

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
                    # sudo: res.company - context is required by ir.rules
                    allowed_company_ids=user_id.sudo().company_ids.ids
                )
                store = Store(user_channels)
                notifications.append((partner, 'mail.record/insert', store.get_result()))
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

    def set_message_pin(self, message_id, pinned):
        """ (Un)pin a message on the channel and send a notification to the
        members.
        :param message_id: id of the message to be pinned.
        :param pinned: whether the message should be pinned or unpinned.
        """
        self.ensure_one()
        message_to_update = self.env['mail.message'].search([
            ['id', '=', message_id],
            ['model', '=', 'discuss.channel'],
            ['res_id', '=', self.id],
            ['pinned_at', '=' if pinned else '!=', False]
        ])
        if not message_to_update:
            return
        message_to_update.flush_recordset(['pinned_at'])
        # Use SQL because by calling write method, write_date is going to be updated, but we don't want pin/unpin
        # a message changes the write_date
        self.env.cr.execute("UPDATE mail_message SET pinned_at=%s WHERE id=%s",
                            (fields.Datetime.now() if pinned else None, message_to_update.id))
        message_to_update.invalidate_recordset(['pinned_at'])

        self.env['bus.bus']._sendone(self, 'mail.record/insert', {
            'Message': {
                'id': message_id,
                'pinned_at': fields.Datetime.to_string(message_to_update.pinned_at),
            }
        })
        if pinned:
            notification_text = '''
                <div data-oe-type="pin" class="o_mail_notification">
                    %(user_pinned_a_message_to_this_channel)s
                    <a href="#" data-oe-type="pin-menu">%(see_all_pins)s</a>
                </div>
            '''
            notification = Markup(notification_text) % {
                'user_pinned_a_message_to_this_channel': Markup('<a href="#" data-oe-type="highlight" data-oe-id="%s">%s</a>') % (
                    message_id,
                    _('%(user_name)s pinned a message to this channel.', user_name=self.env.user.display_name),
                ),
                'see_all_pins': _('See all pinned messages.'),
            }
            self.message_post(body=notification, message_type="notification", subtype_xmlid="mail.mt_comment")

    def _find_or_create_member_for_self(self):
        self.ensure_one()
        domain = [("channel_id", "=", self.id), ("is_self", "=", True)]
        member = self.env["discuss.channel.member"].search(domain)
        if member:
            return member
        if not self.env.user._is_public():
            return self.add_members(partner_ids=self.env.user.partner_id.ids)
        guest = self.env["mail.guest"]._get_guest_from_context()
        if guest:
            return self.add_members(guest_ids=guest.ids)
        return self.env["discuss.channel.member"]

    def _find_or_create_persona_for_channel(self, guest_name, timezone, country_code, post_joined_message=True):
        """
        :param channel: channel to add the persona to
        :param guest_name: name of the persona
        :param post_joined_message: whether to post a message to the channel
            to notify that the persona joined
        :return tuple(partner, guest):
        """
        self.ensure_one()
        guest = self.env["mail.guest"]
        member = self.env["discuss.channel.member"].search([("channel_id", "=", self.id), ("is_self", "=", True)])
        if member:
            return member.partner_id, member.guest_id
        if not self.env.user._is_public():
            self.add_members([self.env.user.partner_id.id], post_joined_message=post_joined_message)
        else:
            guest = self.env["mail.guest"]._get_guest_from_context()
            if not guest:
                guest = self.env["mail.guest"].create(
                    {
                        "country_id": self.env["res.country"].search([("code", "=", country_code)]).id,
                        "lang": get_lang(self.env).code,
                        "name": guest_name,
                        "timezone": timezone,
                    }
                ).sudo(False)
                guest._set_auth_cookie()
                self = self.with_context(guest=guest)
            self.add_members(guest_ids=guest.ids, post_joined_message=post_joined_message)
        return self.env.user.partner_id if not guest else self.env["res.partner"], guest

    @api.model
    def _get_channels_as_member(self):
        # 2 different queries because the 2 sub-queries together with OR are less efficient
        member_domain = [("channel_type", "in", ("channel", "group")), ("is_member", "=", True)]
        pinned_member_domain = [
                ("channel_type", "not in", ("channel", "group")),
                ("channel_member_ids", "any", [("is_self", "=", True), ("is_pinned", "=", True)]),
            ]
        channels = self.env["discuss.channel"].search(member_domain)
        channels += self.env["discuss.channel"].search(pinned_member_domain)
        return channels

    def _channel_basic_info(self):
        self.ensure_one()
        return {
            'avatarCacheKey': self.avatar_cache_key,
            'channel_type': self.channel_type,
            'memberCount': self.member_count,
            'id': self.id,
            'name': self.name,
            'defaultDisplayMode': self.default_display_mode,
            'description': self.description,
            'uuid': self.uuid,
            'group_based_subscription': bool(self.group_ids),
            'create_uid': self.create_uid.id,
            'authorizedGroupFullName': self.group_public_id.full_name,
            'allow_public_upload': self.allow_public_upload,
            'model': "discuss.channel",
            'last_interest_dt': fields.Datetime.to_string(self.last_interest_dt),
        }

    def _to_store(self, store: Store):
        """Adds channel data to the given store."""
        if not self:
            return []
        # sudo: bus.bus: reading non-sensitive last id
        bus_last_id = self.env["bus.bus"].sudo()._bus_last_id()
        # sudo: discuss.channel.rtc.session - reading sessions of accessible channel is acceptable
        store.add(self.sudo().rtc_session_ids, extra=True)
        current_partner, current_guest = self.env["res.partner"]._get_current_persona()
        self.env['discuss.channel'].flush_model()
        self.env['discuss.channel.member'].flush_model()
        # Query instead of ORM for performance reasons: "LEFT JOIN" is more
        # efficient than "id IN" for the cross-table condition between channel
        # (for channel_type) and member (for other fields).
        self.env.cr.execute("""
                 SELECT discuss_channel_member.id
                   FROM discuss_channel_member
              LEFT JOIN discuss_channel
                     ON discuss_channel.id = discuss_channel_member.channel_id
                    AND discuss_channel.channel_type != 'channel'
                  WHERE discuss_channel_member.channel_id in %(channel_ids)s
                    AND (
                        discuss_channel.id IS NOT NULL
                     OR discuss_channel_member.rtc_inviting_session_id IS NOT NULL
                     OR discuss_channel_member.partner_id = %(current_partner_id)s
                     OR discuss_channel_member.guest_id = %(current_guest_id)s
                    )
               ORDER BY discuss_channel_member.id ASC
        """, {'channel_ids': tuple(self.ids), 'current_partner_id': current_partner.id or None, 'current_guest_id': current_guest.id or None})
        all_needed_members = self.env['discuss.channel.member'].browse([m['id'] for m in self.env.cr.dictfetchall()])
        all_needed_members._to_store(Store())  # prefetch in batch
        members_by_channel = defaultdict(lambda: self.env['discuss.channel.member'])
        invited_members_by_channel = defaultdict(lambda: self.env['discuss.channel.member'])
        member_of_current_user_by_channel = defaultdict(lambda: self.env['discuss.channel.member'])
        for member in all_needed_members:
            members_by_channel[member.channel_id] += member
            if member.rtc_inviting_session_id:
                invited_members_by_channel[member.channel_id] += member
            if (current_partner and member.partner_id == current_partner) or (current_guest and member.guest_id == current_guest):
                member_of_current_user_by_channel[member.channel_id] = member
        for channel in self:
            member = member_of_current_user_by_channel.get(channel, self.env['discuss.channel.member']).with_prefetch([m.id for m in member_of_current_user_by_channel.values()])
            info = channel._channel_basic_info()
            info["is_editable"] = channel.is_editable
            info["fetchChannelInfoState"] = "fetched"
            # find the channel member state
            if current_partner or current_guest:
                info['message_needaction_counter'] = channel.message_needaction_counter
                info["message_needaction_counter_bus_id"] = bus_last_id
                if member:
                    store.add(
                        member,
                        extra_fields={
                            "last_interest_dt": True,
                            "message_unread_counter": True,
                            "message_unread_counter_bus_id": bus_last_id,
                            "new_message_separator": True
                        },
                    )
                    info['state'] = member.fold_state or 'closed'
                    info['custom_notifications'] = member.custom_notifications
                    info['mute_until_dt'] = fields.Datetime.to_string(member.mute_until_dt)
                    info['custom_channel_name'] = member.custom_channel_name
                    info['is_pinned'] = member.is_pinned
                    if member.rtc_inviting_session_id:
                        info["rtcInvitingSession"] = {"id": member.rtc_inviting_session_id.id}
            # add members info
            if channel.channel_type != 'channel':
                # avoid sending potentially a lot of members for big channels
                # exclude chat and other small channels from this optimization because they are
                # assumed to be smaller and it's important to know the member list for them
                store.add(members_by_channel[channel] - member)
            # add RTC sessions info
            invited_members = invited_members_by_channel[channel]
            store.add(
                invited_members,
                fields={
                    "id": True,
                    "channel": {},
                    "persona": {
                        "partner": {"id": True, "name": True, "im_status": True},
                        "guest": {"id": True, "name": True, "im_status": True},
                    },
                },
            )
            info["invitedMembers"] = [("ADD", [{"id": member.id} for member in invited_members])]
            info["rtcSessions"] = [
                # sudo: discuss.channel.rtc.session - reading sessions of accessible channel is acceptable
                ("ADD", [{"id": session.id} for session in channel.sudo().rtc_session_ids])
            ]
            store.add("Thread", info)

    # User methods
    @api.model
    @api.returns('self', lambda channels: Store(channels).get_result())
    def channel_get(self, partners_to, pin=True, force_open=False):
        """ Get the canonical private channel between some partners, create it if needed.
            To reuse an old channel (conversation), this one must be private, and contains
            only the given partners.
            :param partners_to : list of res.partner ids to add to the conversation
            :param pin : True if getting the channel should pin it for the current user
            :param force_open : True if getting the channel should open it for the current user
            :returns: channel_info of the created or existing channel
            :rtype: dict
        """
        if self.env.user.partner_id.id not in partners_to:
            partners_to.append(self.env.user.partner_id.id)
        if len(partners_to) > 2:
            raise UserError(_("A chat should not be created with more than 2 persons. Create a group instead."))
        # determine type according to the number of partner in the channel
        self.flush_model()
        self.env['discuss.channel.member'].flush_model()
        self.env.cr.execute("""
            SELECT M.channel_id
            FROM discuss_channel C, discuss_channel_member M
            WHERE M.channel_id = C.id
                AND M.partner_id IN %s
                AND C.channel_type LIKE 'chat'
                AND NOT EXISTS (
                    SELECT 1
                    FROM discuss_channel_member M2
                    WHERE M2.channel_id = C.id
                        AND M2.partner_id NOT IN %s
                )
            GROUP BY M.channel_id
            HAVING ARRAY_AGG(DISTINCT M.partner_id ORDER BY M.partner_id) = %s
            LIMIT 1
        """, (tuple(partners_to), tuple(partners_to), sorted(list(partners_to)),))
        result = self.env.cr.dictfetchall()
        if result:
            # get the existing channel between the given partners
            channel = self.browse(result[0].get('channel_id'))
            # pin or open the channel for the current partner
            if pin or force_open:
                member = self.env['discuss.channel.member'].search([('partner_id', '=', self.env.user.partner_id.id), ('channel_id', '=', channel.id)])
                vals = {'last_interest_dt': fields.Datetime.now()}
                if pin:
                    vals['unpin_dt'] = False
                if force_open:
                    vals['fold_state'] = "open"
                member.write(vals)
            channel._broadcast(self.env.user.partner_id.ids)
        else:
            # create a new one
            channel = self.create({
                'channel_member_ids': [
                    Command.create({
                        'partner_id': partner_id,
                        # only pin for the current user, so the chat does not show up for the correspondent until a message has been sent
                        # manually set the last_interest_dt to make sure that it works well with the default last_interest_dt (datetime.now())
                        'unpin_dt': False if partner_id == self.env.user.partner_id.id else fields.Datetime.now(),
                        'last_interest_dt': fields.Datetime.now() if partner_id == self.env.user.partner_id.id else fields.Datetime.now() - timedelta(seconds=30),
                    }) for partner_id in partners_to
                ],
                'channel_type': 'chat',
                'name': ', '.join(self.env['res.partner'].browse(partners_to).mapped('name')),
            })
            channel._broadcast(partners_to)
        return channel

    def channel_pin(self, pinned=False):
        self.ensure_one()
        member = self.env['discuss.channel.member'].search(
            [('partner_id', '=', self.env.user.partner_id.id), ('channel_id', '=', self.id), ('is_pinned', '!=', pinned)])
        if member:
            member.write({'unpin_dt': False if pinned else fields.Datetime.now()})
        if not pinned:
            self.env['bus.bus']._sendone(self.env.user.partner_id, 'discuss.channel/unpin', {'id': self.id})
        else:
            store = Store(self)
            self.env['bus.bus']._sendone(self.env.user.partner_id, 'mail.record/insert', store.get_result())

    def _types_allowing_seen_infos(self):
        """ Return the channel types which allow sending seen infos notification
        on the channel """
        return ["chat", "group"]

    def channel_fetched(self):
        """ Broadcast the channel_fetched notification to channel members
        """
        for channel in self:
            if not channel.message_ids.ids:
                continue
            # a bit not-modular but helps understanding code
            if channel.channel_type not in {'chat', 'whatsapp'}:
                continue
            last_message_id = channel.message_ids.ids[0] # zero is the index of the last message
            member = self.env['discuss.channel.member'].search([('channel_id', '=', channel.id), ('partner_id', '=', self.env.user.partner_id.id)], limit=1)
            if not member:
                # member not a part of the channel
                continue
            if member.fetched_message_id.id == last_message_id:
                # last message fetched by user is already up-to-date
                continue
            # Avoid serialization error when multiple tabs are opened.
            query = """
                UPDATE discuss_channel_member
                SET fetched_message_id = %s
                WHERE id IN (
                    SELECT id FROM discuss_channel_member WHERE id = %s
                    FOR NO KEY UPDATE SKIP LOCKED
                )
            """
            self.env.cr.execute(query, (last_message_id, member.id))
            self.env['bus.bus']._sendone(channel, 'discuss.channel.member/fetched', {
                'channel_id': channel.id,
                'id': member.id,
                'last_message_id': last_message_id,
                'partner_id': self.env.user.partner_id.id,
            })

    def channel_set_custom_name(self, name):
        self.ensure_one()
        member = self.env['discuss.channel.member'].search([('partner_id', '=', self.env.user.partner_id.id), ('channel_id', '=', self.id)])
        member.write({'custom_channel_name': name})
        self.env['bus.bus']._sendone(member.partner_id, 'mail.record/insert', {
            'Thread': {
                'custom_channel_name': name,
                'id': self.id,
                'model': "discuss.channel",
            }
        })

    def channel_rename(self, name):
        self.ensure_one()
        self.write({'name': name})

    def channel_change_description(self, description):
        self.ensure_one()
        self.write({'description': description})

    def channel_join(self):
        """Shortcut to add the current user as member of self channels.
        Prefer calling add_members() directly when possible.
        """
        self.add_members(self.env.user.partner_id.ids)

    @api.model
    @api.returns('self', lambda channels: Store(channels).get_result())
    def channel_create(self, name, group_id):
        """ Create a channel and add the current partner, broadcast it (to make the user directly
            listen to it when polling)
            :param name : the name of the channel to create
            :param group_id : the group allowed to join the channel.
            :return dict : channel header
        """
        # create the channel
        vals = {
            'channel_type': 'channel',
            'name': name,
        }
        new_channel = self.create(vals)
        group = self.env['res.groups'].search([('id', '=', group_id)]) if group_id else None
        new_channel.group_public_id = group.id if group else None
        notification = Markup('<div class="o_mail_notification">%s</div>') % _("created this channel.")
        new_channel.message_post(body=notification, message_type="notification", subtype_xmlid="mail.mt_comment")
        store = Store(new_channel)
        self.env['bus.bus']._sendone(self.env.user.partner_id, 'mail.record/insert', store.get_result())
        return new_channel

    @api.model
    @api.returns('self', lambda channels: Store(channels).get_result())
    def create_group(self, partners_to, default_display_mode=False, name=''):
        """ Creates a group channel.

            :param partners_to : list of res.partner ids to add to the conversation
            :param str default_display_mode: how the channel will be displayed by default
            :param str name: group name. default name is computed client side from the list of members if no name is set
            :returns: channel_info of the created channel
            :rtype: dict
        """
        partners_to = set(partners_to)
        channel = self.create({
            'channel_member_ids': [Command.create({'partner_id': partner_id}) for partner_id in partners_to],
            'channel_type': 'group',
            'default_display_mode': default_display_mode,
            'name': name,
        })
        channel._broadcast(channel.channel_member_ids.partner_id.ids)
        return channel

    @api.model
    def get_mention_suggestions(self, search, limit=8):
        """ Return 'limit'-first channels' id, name, channel_type and authorizedGroupFullName fields such that the
            name matches a 'search' string. Exclude channels of type chat (DM) and group.
        """
        domain = expression.AND([
                        [('name', 'ilike', search)],
                        [('channel_type', '=', 'channel')],
                        [('channel_partner_ids', 'in', [self.env.user.partner_id.id])]
                    ])
        channels = self.search(domain, limit=limit)
        return [{
            'authorizedGroupFullName': channel.group_public_id.full_name,
            'channel_type': channel.channel_type,
            'model': "discuss.channel",
            'id': channel.id,
            'name': channel.name,
        } for channel in channels]

    def _get_last_messages(self):
        """ Return the last message for each of the given channels."""
        if not self:
            return self.env["mail.message"]
        self.env['mail.message'].flush_model()
        self.env.cr.execute(
            """
                   SELECT last_message_id
                     FROM discuss_channel
        LEFT JOIN LATERAL (
                              SELECT id
                                FROM mail_message
                               WHERE mail_message.model = 'discuss.channel'
                                 AND mail_message.res_id = discuss_channel.id
                            ORDER BY id DESC
                               LIMIT 1
                          ) AS t(last_message_id) ON TRUE
                    WHERE discuss_channel.id IN %(ids)s
                 GROUP BY discuss_channel.id, t.last_message_id
                 ORDER BY discuss_channel.id
            """,
            {"ids": tuple(self.ids)},
        )
        return self.env["mail.message"].browse([mid for (mid,) in self.env.cr.fetchall() if mid])

    def _load_more_members(self, known_member_ids):
        self.ensure_one()
        unknown_members = self.env['discuss.channel.member'].search(
            domain=[('id', 'not in', known_member_ids), ('channel_id', '=', self.id)],
            limit=100
        )
        count = self.env['discuss.channel.member'].search_count(
            domain=[('channel_id', '=', self.id)],
        )
        store = Store(unknown_members)
        store.add(
            "Thread",
            {
                "id": self.id,
                "model": "discuss.channel",
                "memberCount": count,
            },
        )
        return store.get_result()

    # ------------------------------------------------------------
    # COMMANDS
    # ------------------------------------------------------------

    def _send_transient_message(self, partner_to, content):
        """ Notifies partner_to that a message (not stored in DB) has been
            written in this channel.
            `content` is HTML, dynamic parts should be escaped by the caller.
        """
        self.env['bus.bus']._sendone(partner_to, 'discuss.channel/transient_message', {
            'body': f"<span class='o_mail_notification'>{content}</span>",
            'thread': {'model': self._name, 'id': self.id},
        })

    def execute_command_help(self, **kwargs):
        if self.channel_type == 'channel':
            msg = html_escape(_("You are in channel %(bold_start)s#%(channel_name)s%(bold_end)s.")) % {
                "bold_start": Markup("<b>"),
                "bold_end": Markup("</b>"),
                "channel_name": self.name,
            }
        else:
            all_channel_members = self.env['discuss.channel.member'].with_context(active_test=False)
            channel_members = all_channel_members.search([("is_self", "=", False), ("channel_id", "=", self.id)], order='id asc')
            if channel_members:
                member_names = Markup(
                    format_list(
                        self.env,
                        [f"<b>@%(member_{member.id})s</b>" for member in channel_members],
                    )
                ) % {
                    f"member_{member.id}": member.partner_id.name or member.guest_id.name for member in channel_members
                }
                msg = html_escape(_("You are in a private conversation with %(member_names)s.")) % {
                    "member_names": member_names,
                }
            else:
                msg = _("You are alone in a private conversation.")
        msg += self._execute_command_help_message_extra()
        self._send_transient_message(self.env.user.partner_id, msg)

    def _execute_command_help_message_extra(self):
        msg = html_escape(
            _(
                "%(new_line)s"
                "%(new_line)sType %(bold_start)s@username%(bold_end)s to mention someone, and grab their attention."
                "%(new_line)sType %(bold_start)s#channel%(bold_end)s to mention a channel."
                "%(new_line)sType %(bold_start)s/command%(bold_end)s to execute a command."
                "%(new_line)sType %(bold_start)s:shortcut%(bold_end)s to insert a canned response in your message."
            )
        ) % {"bold_start": Markup("<b>"), "bold_end": Markup("</b>"), "new_line": Markup("<br>")}
        return msg

    def execute_command_leave(self, **kwargs):
        if self.channel_type in ('channel', 'group'):
            self.action_unfollow()
        else:
            self.channel_pin(False)

    def execute_command_who(self, **kwargs):
        channel_members = self.env['discuss.channel.member'].with_context(active_test=False).search([('partner_id', '!=', self.env.user.partner_id.id), ('channel_id', '=', self.id)])
        members = [
            m.partner_id._get_html_link(title=f"@{m.partner_id.name}") if m.partner_id else f'<strong>@{html_escape(m.guest_id.name)}</strong>'
            for m in channel_members[:30]
        ]
        if len(members) == 0:
            msg = _("You are alone in this channel.")
        else:
            dots = "..." if len(members) != len(channel_members) else ""
            msg = _("Users in this channel: %(members)s %(dots)s and you.", members=", ".join(members), dots=dots)

        self._send_transient_message(self.env.user.partner_id, msg)
