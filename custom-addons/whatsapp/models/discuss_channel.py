# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from datetime import timedelta
from markupsafe import Markup

from odoo import api, Command, fields, models, tools, _
from odoo.addons.whatsapp.tools import phone_validation as wa_phone_validation
from odoo.exceptions import ValidationError
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT


_logger = logging.getLogger(__name__)

class DiscussChannel(models.Model):
    """ Support WhatsApp Channels, used for discussion with a specific
    whasapp number """
    _inherit = 'discuss.channel'

    channel_type = fields.Selection(
        selection_add=[('whatsapp', 'WhatsApp Conversation')],
        ondelete={'whatsapp': 'cascade'})
    whatsapp_number = fields.Char(string="Phone Number")
    whatsapp_channel_valid_until = fields.Datetime(string="WhatsApp Partner Last Message Datetime", compute="_compute_whatsapp_channel_valid_until")
    whatsapp_partner_id = fields.Many2one(comodel_name='res.partner', string="WhatsApp Partner", index='btree_not_null')
    whatsapp_mail_message_id = fields.Many2one(comodel_name='mail.message', string="Related message", index="btree_not_null")
    wa_account_id = fields.Many2one(comodel_name='whatsapp.account', string="WhatsApp Business Account")

    _sql_constraints = [
        ('group_public_id_check',
         "CHECK (channel_type = 'channel' OR channel_type = 'whatsapp' OR group_public_id IS NULL)",
         'Group authorization and group auto-subscription are only supported on channels and whatsapp.'),
    ]

    @api.constrains('channel_type', 'whatsapp_number')
    def _check_whatsapp_number(self):
        # constraint to check the whatsapp number for channel with type 'whatsapp'
        missing_number = self.filtered(lambda channel: channel.channel_type == 'whatsapp' and not channel.whatsapp_number)
        if missing_number:
            raise ValidationError(
                _("A phone number is required for WhatsApp channels %(channel_names)s",
                  channel_names=', '.join(missing_number)
                ))

    # INHERITED CONSTRAINTS

    @api.constrains('group_public_id', 'group_ids')
    def _constraint_group_id_channel(self):
        valid_channels = self.filtered(lambda channel: channel.channel_type == 'whatsapp')
        super(DiscussChannel, self - valid_channels)._constraint_group_id_channel()

    # NEW COMPUTES

    @api.depends('message_ids')
    def _compute_whatsapp_channel_valid_until(self):
        self.whatsapp_channel_valid_until = False
        wa_channels = self.filtered(lambda c: c.channel_type == 'whatsapp')
        if wa_channels:
            channel_last_msg_ids = {
                r['id']: r['message_id']
                for r in wa_channels._channel_last_whatsapp_partner_id_message_ids()
            }
            MailMessage = self.env['mail.message'].with_prefetch(list(channel_last_msg_ids.values()))
            for channel in wa_channels:
                last_msg_id = channel_last_msg_ids.get(channel.id, False)
                if not last_msg_id:
                    continue
                channel.whatsapp_channel_valid_until = MailMessage.browse(last_msg_id).create_date + timedelta(hours=24)

    def _channel_last_whatsapp_partner_id_message_ids(self):
        """ Return the last message of the whatsapp_partner_id given whatsapp channels."""
        if not self:
            return []
        self.env['mail.message'].flush_model()
        self.env.cr.execute("""
              SELECT res_id AS id, MAX(mm.id) AS message_id
                FROM mail_message AS mm
                JOIN discuss_channel AS dc ON mm.res_id = dc.id
               WHERE mm.model = 'discuss.channel'
                 AND mm.res_id IN %s
                 AND mm.author_id = dc.whatsapp_partner_id
            GROUP BY mm.res_id
            """, [tuple(self.ids)])
        return self.env.cr.dictfetchall()

    # INHERITED COMPUTES

    def _compute_is_chat(self):
        super()._compute_is_chat()
        self.filtered(lambda channel: channel.channel_type == 'whatsapp').is_chat = True

    def _compute_group_public_id(self):
        wa_channels = self.filtered(lambda channel: channel.channel_type == "whatsapp")
        wa_channels.filtered(lambda channel: not channel.group_public_id).group_public_id = self.env.ref('base.group_user')
        super(DiscussChannel, self - wa_channels)._compute_group_public_id()

    # ------------------------------------------------------------
    # MAILING
    # ------------------------------------------------------------

    def _get_notify_valid_parameters(self):
        if self.channel_type == 'whatsapp':
            return super()._get_notify_valid_parameters() | {'whatsapp_inbound_msg_uid'}
        return super()._get_notify_valid_parameters()

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        recipients_data = super()._notify_thread(message, msg_vals=msg_vals, **kwargs)
        if kwargs.get('whatsapp_inbound_msg_uid') and self.channel_type == 'whatsapp':
            self.env['whatsapp.message'].create({
                'mail_message_id': message.id,
                'message_type': 'inbound',
                'mobile_number': f'+{self.whatsapp_number}',
                'msg_uid': kwargs['whatsapp_inbound_msg_uid'],
                'state': 'received',
                'wa_account_id': self.wa_account_id.id,
            })
        return recipients_data

    def message_post(self, *, message_type='notification', **kwargs):
        new_msg = super().message_post(message_type=message_type, **kwargs)
        if self.channel_type == 'whatsapp' and message_type == 'whatsapp_message':
            if new_msg.author_id == self.whatsapp_partner_id:
                self.env['bus.bus']._sendone(self, 'discuss.channel/whatsapp_channel_valid_until_changed', {
                    'id': self.id,
                    'whatsapp_channel_valid_until': self.whatsapp_channel_valid_until,
                })
            if not new_msg.wa_message_ids:
                whatsapp_message = self.env['whatsapp.message'].create({
                    'body': new_msg.body,
                    'mail_message_id': new_msg.id,
                    'message_type': 'outbound',
                    'mobile_number': f'+{self.whatsapp_number}',
                    'wa_account_id': self.wa_account_id.id,
                })
                whatsapp_message._send()
        return new_msg

    # ------------------------------------------------------------
    # CONTROLLERS
    # ------------------------------------------------------------

    @api.returns('self')
    def _get_whatsapp_channel(self, whatsapp_number, wa_account_id, sender_name=False, create_if_not_found=False, related_message=False):
        """ Creates a whatsapp channel.

        :param str whatsapp_number: whatsapp phone number of the customer. It should
          be formatted according to whatsapp standards, aka {country_code}{national_number}.

        :returns: whatsapp discussion discuss.channel
        """
        # be somewhat defensive with number, as it is used in various flows afterwards
        # notably in 'message_post' for the number, and called by '_process_messages'
        base_number = whatsapp_number if whatsapp_number.startswith('+') else f'+{whatsapp_number}'
        wa_number = base_number.lstrip('+')
        wa_formatted = wa_phone_validation.wa_phone_format(
            self.env.company,
            number=base_number,
            force_format="WHATSAPP",
            raise_exception=False,
        ) or wa_number

        related_record = False
        responsible_partners = self.env['res.partner']
        channel_domain = [
            ('whatsapp_number', '=', wa_formatted),
            ('wa_account_id', '=', wa_account_id.id)
        ]
        if related_message:
            related_record = self.env[related_message.model].browse(related_message.res_id)
            responsible_partners = related_record._whatsapp_get_responsible(
                related_message=related_message,
                related_record=related_record,
                whatsapp_account=wa_account_id,
            ).partner_id

            if 'message_ids' in related_record:
                record_messages = related_record.message_ids
            else:
                record_messages = self.env['mail.message'].search([
                    ('model', '=', related_record._name),
                    ('res_id', '=', related_record.id),
                    ('message_type', '!=', 'user_notification'),
                ])
            channel_domain += [
                ('whatsapp_mail_message_id', 'in', record_messages.ids),
            ]
        channel = self.sudo().search(channel_domain, order='create_date desc', limit=1)
        if responsible_partners:
            channel = channel.filtered(lambda c: all(r in c.channel_member_ids.partner_id for r in responsible_partners))

        partners_to_notify = responsible_partners
        record_name = related_message.record_name
        if not record_name and related_message.res_id:
            record_name = self.env[related_message.model].browse(related_message.res_id).display_name
        if not channel and create_if_not_found:
            channel = self.sudo().with_context(tools.clean_context(self.env.context)).create({
                'name': f"{wa_formatted} ({record_name})" if record_name else wa_formatted,
                'channel_type': 'whatsapp',
                'whatsapp_number': wa_formatted,
                'whatsapp_partner_id': self.env['res.partner']._find_or_create_from_number(wa_formatted, sender_name).id,
                'wa_account_id': wa_account_id.id,
                'whatsapp_mail_message_id': related_message.id if related_message else None,
            })
            partners_to_notify += channel.whatsapp_partner_id
            if related_message:
                # Add message in channel about the related document
                info = _("Related %(model_name)s: ", model_name=self.env['ir.model']._get(related_message.model).display_name)
                url = Markup('{base_url}/web#model={model}&id={res_id}').format(
                    base_url=self.get_base_url(), model=related_message.model, res_id=related_message.res_id)
                related_record_name = related_message.record_name
                if not related_record_name:
                    related_record_name = self.env[related_message.model].browse(related_message.res_id).display_name
                channel.message_post(
                    body=Markup('<p>{info}<a target="_blank" href="{url}">{related_record_name}</a></p>').format(
                        info=info, url=url, related_record_name=related_record_name),
                    message_type='comment',
                    author_id=self.env.ref('base.partner_root').id,
                    subtype_xmlid='mail.mt_note',
                )
                if hasattr(related_record, 'message_post'):
                    # Add notification in document about the new message and related channel
                    info = _("A new WhatsApp channel is created for this document")
                    url = Markup('{base_url}/web#model=discuss.channel&id={channel_id}').format(
                        base_url=self.get_base_url(), channel_id=channel.id)
                    related_record.message_post(
                        author_id=self.env.ref('base.partner_root').id,
                        body=Markup('<p>{info}<a target="_blank" class="o_whatsapp_channel_redirect"'
                                    'data-oe-id="{channel_id}" href="{url}">{channel_name}</a></p>').format(
                                        info=info, url=url, channel_id=channel.id, channel_name=channel.display_name),
                        message_type='comment',
                        subtype_xmlid='mail.mt_note',
                    )
            if partners_to_notify == channel.whatsapp_partner_id and wa_account_id.notify_user_ids.partner_id:
                partners_to_notify += wa_account_id.notify_user_ids.partner_id
            channel.channel_member_ids = [Command.clear()] + [Command.create({'partner_id': partner.id}) for partner in partners_to_notify]
            channel._broadcast(partners_to_notify.ids)
        return channel

    def whatsapp_channel_join_and_pin(self):
        """ Adds the current partner as a member of self channel and pins them if not already pinned. """
        self.ensure_one()
        if self.channel_type != 'whatsapp':
            raise ValidationError(_('This join method is not possible for regular channels.'))

        self.check_access_rights('write')
        self.check_access_rule('write')
        current_partner = self.env.user.partner_id
        member = self.channel_member_ids.filtered(lambda m: m.partner_id == current_partner)
        if member:
            if not member.is_pinned:
                member.write({'is_pinned': True})
        else:
            new_member = self.env['discuss.channel.member'].with_context(tools.clean_context(self.env.context)).sudo().create([{
                'partner_id': current_partner.id,
                'channel_id': self.id,
            }])
            message_body = Markup(f'<div class="o_mail_notification">{_("joined the channel")}</div>')
            new_member.channel_id.message_post(body=message_body, message_type="notification", subtype_xmlid="mail.mt_comment")
            self.env['bus.bus']._sendone(self, 'mail.record/insert', {
                'Thread': {
                    'channelMembers': [('ADD', list(new_member._discuss_channel_member_format().values()))],
                    'id': self.id,
                    'memberCount': self.member_count,
                    'model': "discuss.channel",
                }
            })
        return self._channel_info()[0]

    # ------------------------------------------------------------
    # OVERRIDE
    # ------------------------------------------------------------

    def _action_unfollow(self, partner):
        if self.channel_type == 'whatsapp' \
                and ((self.whatsapp_mail_message_id \
                and self.whatsapp_mail_message_id.author_id == partner) \
                or len(self.channel_member_ids) <= 2):
            msg = _("You can't leave this channel. As you are the owner of this WhatsApp channel, you can only delete it.")
            self._send_transient_message(partner, msg)
            return
        super()._action_unfollow(partner)

    def _channel_info(self):
        channel_infos = super()._channel_info()
        channel_infos_dict = {c['id']: c for c in channel_infos}

        for channel in self:
            if channel.channel_type == 'whatsapp':
                channel_infos_dict[channel.id]['whatsapp_channel_valid_until'] = \
                    channel.whatsapp_channel_valid_until.strftime(DEFAULT_SERVER_DATETIME_FORMAT) \
                    if channel.whatsapp_channel_valid_until else False

        return list(channel_infos_dict.values())

    # ------------------------------------------------------------
    # COMMANDS
    # ------------------------------------------------------------

    def execute_command_leave(self, **kwargs):
        if self.channel_type == 'whatsapp':
            self.action_unfollow()
        else:
            super().execute_command_leave(**kwargs)
