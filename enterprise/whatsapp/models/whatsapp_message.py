# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import logging
import threading
from markupsafe import Markup, escape

from datetime import timedelta

from odoo import models, fields, api, _
from odoo.addons.phone_validation.tools import phone_validation
from odoo.addons.whatsapp.tools import phone_validation as wa_phone_validation
from odoo.addons.whatsapp.tools.retryable_codes import WHATSAPP_RETRYABLE_ERROR_CODES
from odoo.addons.whatsapp.tools.bounced_codes import BOUNCED_ERROR_CODES
from odoo.addons.whatsapp.tools.whatsapp_api import WhatsAppApi
from odoo.addons.whatsapp.tools.whatsapp_exception import WhatsAppError
from odoo.exceptions import ValidationError, UserError
from odoo.tools import frozendict, groupby, html2plaintext

_logger = logging.getLogger(__name__)

class WhatsAppMessage(models.Model):
    _name = 'whatsapp.message'
    _description = 'WhatsApp Messages'
    _order = 'id desc'
    _rec_name = 'mobile_number'

    # Refer to https://developers.facebook.com/docs/whatsapp/cloud-api/reference/media/#supported-media-types
    # for more details about supported media types
    _SUPPORTED_ATTACHMENT_TYPE = {
        'audio': ('audio/aac', 'audio/mp4', 'audio/mpeg', 'audio/amr', 'audio/ogg'),
        'document': (
            'text/plain', 'application/pdf', 'application/vnd.ms-powerpoint', 'application/msword',
            'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        ),
        'image': ('image/jpeg', 'image/png'),
        'video': ('video/mp4',),
    }
    # amount of days during which a message is considered active
    # used for GC and for finding an active document channel using a recent whatsapp template message
    _ACTIVE_THRESHOLD_DAYS = 15

    mobile_number = fields.Char(string="Sent To")
    mobile_number_formatted = fields.Char(
        string="Mobile Number Formatted",
        compute="_compute_mobile_number_formatted", readonly=False, store=True)
    message_type = fields.Selection([
        ('outbound', 'Outbound'),
        ('inbound', 'Inbound')], string="Message Type", default='outbound')
    state = fields.Selection(selection=[
        ('outgoing', 'In Queue'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
        ('replied', 'Replied'),  # used internally
        ('received', 'Received'),
        ('error', 'Failed'),
        ('bounced', 'Bounced'),  # failure linked to number usage, different from pure whatsapp error
        ('cancel', 'Cancelled')], string="State", default='outgoing')
    failure_type = fields.Selection([
        ('account', 'Account Error'),
        ('blacklisted', 'Blacklisted Phone Number'),
        ('network', 'Network Error'),
        ('outdated_channel', 'The channel is no longer active'),
        ('phone_invalid', 'Wrong Number Format'),
        ('template', 'Template Quality Rating Too Low'),
        ('unknown', 'Unknown Error'),
        ('whatsapp_recoverable', 'Identified Error'),
        ('whatsapp_unrecoverable', 'Other Technical Error')
    ])
    failure_reason = fields.Char(string="Failure Reason", help="Usually an error message from Whatsapp")
    free_text_json = fields.Json(string="Free Text Template Parameters")
    wa_template_id = fields.Many2one(comodel_name='whatsapp.template')
    msg_uid = fields.Char(string="WhatsApp Message ID")
    wa_account_id = fields.Many2one(comodel_name='whatsapp.account', string="WhatsApp Business Account")
    parent_id = fields.Many2one('whatsapp.message', 'Response To', index='btree_not_null', ondelete="set null")

    mail_message_id = fields.Many2one(comodel_name='mail.message', index=True)
    body = fields.Html(related='mail_message_id.body', string="Body", related_sudo=False)

    _sql_constraints = [
        ('unique_msg_uid', 'unique(msg_uid)', "Each whatsapp message should correspond to a single message uuid.")
    ]

    @api.depends('mobile_number')
    def _compute_mobile_number_formatted(self):
        for message in self:
            recipient_partner = message.mail_message_id.partner_ids[0] if message.mail_message_id.partner_ids else self.env['res.partner']
            country = recipient_partner.country_id if recipient_partner.country_id else self.env.company.country_id
            formatted = wa_phone_validation.wa_phone_format(
                country,  # could take mail.message record as context but seems overkill
                number=message.mobile_number,
                country=country,
                force_format="WHATSAPP",
                raise_exception=False,
            )
            message.mobile_number_formatted = formatted or ''

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals):
        """Override to check blacklist number and also add to blacklist if user has send stop message."""
        messages = super().create(vals)
        for message in messages:
            body = html2plaintext(message.body)
            if message.message_type == 'inbound' and message.mobile_number_formatted:
                body_message = re.findall('([a-zA-Z]+)', body)
                message_string = "".join(i.lower() for i in body_message)
                try:
                    if message_string in self._get_opt_out_message():
                        self.env['phone.blacklist'].sudo().add(
                            number=wa_phone_validation.wa_phone_format_for_blacklist(message.mobile_number_formatted),
                            message=_("User has been opt out of receiving WhatsApp messages"),
                        )
                    else:
                        self.env['phone.blacklist'].sudo().remove(
                            number=wa_phone_validation.wa_phone_format_for_blacklist(message.mobile_number_formatted),
                            message=_("User has opted in to receiving WhatsApp messages"),
                        )
                except UserError:
                    # there was something wrong with number formatting that cannot be
                    # accepted by the blacklist -> simply skip, better be defensive
                    _logger.warning(
                        'Whatsapp: impossible to change opt-in status of %s (formatted as %s) as it is not a valid number (whatsapp.message-%s)',
                        message.mobile_number, message.mobile_number_formatted, message.id
                    )
        return messages

    @api.autovacuum
    def _gc_whatsapp_messages(self):
        """ To avoid bloating the database, we remove old whatsapp.messages that have been correctly
        received / sent and are older than 15 days.'

        We use these messages mainly to tie a customer answer to a certain document channel, but
        only do so for the last 15 days (see '_find_active_channel').

        After that period, they become non-relevant as the real content of conversations is kept
        inside discuss.channel / mail.messages (as every other discussions).

        Impact of GC when using the 'reply-to' function from the WhatsApp app as the customer:
          - We could loose the context that a message is 'a reply to' another one, implying that
          someone would reply to a message after 15 days, which is unlikely.
          (To clarify: we will still receive the message, it will just not give the 'in-reply-to'
          context anymore on the discuss channel).
          - We could also loose the "right channel" in that case, and send the message to a another
          (or a new) discuss channel, but it is again unlikely to answer more than 15 days later. """

        domain = self._get_whatsapp_gc_domain()
        self.env['whatsapp.message'].search(domain).unlink()

    def _get_whatsapp_gc_domain(self):
        date_threshold = fields.Datetime.now() - timedelta(
            days=self.env['whatsapp.message']._ACTIVE_THRESHOLD_DAYS)
        return [
            ('create_date', '<', date_threshold),
            ('state', 'not in', ['outgoing', 'error', 'cancel'])
        ]

    def _get_formatted_number(self, sanitized_number, country_code):
        """ Format a valid mobile number for whatsapp.

        :examples:
        '+919999912345' -> '919999912345'
        :return: formatted mobile number

        TDE FIXME: remove in master
        """
        mobile_number_parse = phone_validation.phone_parse(sanitized_number, country_code)
        return f'{mobile_number_parse.country_code}{mobile_number_parse.national_number}'

    @api.model
    def _get_opt_out_message(self):
        return ['stop', 'unsubscribe', 'stop promotions']

    # ------------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------------

    def button_resend(self):
        """ Resend a failed message. """
        if self.filtered(lambda rec: rec.state != 'error'):
            raise UserError(_("You can not resend message which is not in failed state."))
        self._resend_failed()

    def button_cancel_send(self):
        """ Cancel a draft or outgoing message. """
        if self.filtered(lambda rec: rec.state != 'outgoing'):
            raise UserError(_("You can not cancel message which is in queue."))
        self.state = 'cancel'

    # ------------------------------------------------------------
    # SEND
    # ------------------------------------------------------------

    def _resend_failed(self):
        """Resend failed template messages and messages in active discuss channels."""
        retryable_messages = self.filtered(lambda msg: msg.state == 'error' and msg.failure_type != 'whatsapp_unrecoverable')

        # filter out outdated channel messages to avoid spamming whatsapp
        discuss_messages = retryable_messages.filtered(lambda msg: msg.mail_message_id.model == 'discuss.channel')
        discuss_channel_ids = discuss_messages.mail_message_id.mapped('res_id')
        valid_discuss_channels = self.env['discuss.channel'].browse(discuss_channel_ids).exists().filtered(
            lambda channel: channel.whatsapp_channel_valid_until
            and channel.whatsapp_channel_valid_until >= fields.Datetime.now()  # worst case, they will fail
        )
        cancelled_discuss_messages = discuss_messages.filtered(
            lambda msg: msg.mail_message_id.res_id not in valid_discuss_channels.ids
        )
        retryable_messages = retryable_messages - cancelled_discuss_messages

        cancelled_discuss_messages.write({'state': 'cancel', 'failure_type': 'outdated_channel'})
        retryable_messages.write({'state': 'outgoing', 'failure_type': False, 'failure_reason': False})
        self.env.ref('whatsapp.ir_cron_send_whatsapp_queue')._trigger()

    def _send_cron(self):
        """ Send all outgoing messages. """
        # order by template to have more relevant duplicate detection
        # order descending so non-template messages are processed first, as they have a time limit
        records = self.search([
            ('state', '=', 'outgoing'),
        ], order='wa_template_id', limit=500)
        # should not commit during tests
        records._send_message(with_commit=not getattr(threading.current_thread(), 'testing', False))
        if len(records) == 500:  # assumes there are more whenever search hits limit
            self.env.ref('whatsapp.ir_cron_send_whatsapp_queue')._trigger()

    def _send(self, force_send_by_cron=False):
        if len(self) <= 1 and not force_send_by_cron:
            self._send_message()
        else:
            self.env.ref('whatsapp.ir_cron_send_whatsapp_queue')._trigger()

    def _send_message(self, with_commit=False):
        """ Prepare json data for sending messages, attachments and templates."""
        # init api
        message_to_api = {}
        for account, messages in groupby(self, lambda msg: msg.wa_account_id):
            if not account:
                messages = self.env['whatsapp.message'].concat(*messages)
                messages.write({
                    'failure_type': 'unknown',
                    'failure_reason': 'Missing whatsapp account for message.',
                    'state': 'error',
                })
                self -= messages
                continue
            wa_api = WhatsAppApi(account)
            for message in messages:
                message_to_api[message] = wa_api

        sent_message_vals = set()
        for whatsapp_message in self:
            wa_api = message_to_api[whatsapp_message]
            # try to make changes with current user (notably due to ACLs), but limit
            # to internal users to avoid crash - rewrite me in master please
            if whatsapp_message.create_uid._is_internal():
                whatsapp_message = whatsapp_message.with_user(whatsapp_message.create_uid)
            if whatsapp_message.state != 'outgoing':
                _logger.info("Message state in %s state so it will not sent.", whatsapp_message.state)
                continue
            is_duplicate = False
            msg_uid = False
            try:
                parent_message_id = False
                # body would always come from plaintext2html hence the url text is already the url and references are redundant
                body = html2plaintext(whatsapp_message.body, include_references=False)
                number = whatsapp_message.mobile_number_formatted
                if not number:
                    raise WhatsAppError(failure_type='phone_invalid')
                blacklist_number = wa_phone_validation.wa_phone_format_for_blacklist(number)
                if self.env['phone.blacklist'].sudo().search_count([('number', 'ilike', blacklist_number), ('active', '=', True)], limit=1):
                    raise WhatsAppError(failure_type='blacklisted')

                # based on template
                if template := whatsapp_message.wa_template_id:
                    message_type = 'template'
                    if whatsapp_message.wa_template_id.status != 'approved' or whatsapp_message.wa_template_id.quality == 'red':
                        raise WhatsAppError(failure_type='template')
                    whatsapp_message.message_type = 'outbound'
                    if whatsapp_message.mail_message_id.model != whatsapp_message.wa_template_id.model:
                        raise WhatsAppError(failure_type='template')

                    RecordModel = self.env[whatsapp_message.mail_message_id.model].with_user(whatsapp_message.env.user)
                    from_record = RecordModel.browse(whatsapp_message.mail_message_id.res_id)

                    # if retrying message then we need to unlink previous attachment
                    # in case of header with report in order to generate it again
                    if whatsapp_message.wa_template_id.report_id and whatsapp_message.wa_template_id.header_type == 'document' and whatsapp_message.mail_message_id.attachment_ids:
                        whatsapp_message.mail_message_id.attachment_ids.unlink()

                    # generate sending values, components and attachments
                    send_vals, attachment = whatsapp_message.wa_template_id._get_send_template_vals(
                        record=from_record,
                        whatsapp_message=whatsapp_message,
                    )
                    # reports are considered always unique
                    if not template.report_id:
                        send_vals_without_attachments = dict(send_vals)
                        # the same attachment re-uploaded will have a different identifier
                        # TODO MASTER avoid having to upload as part of the "get template values" flow
                        if template.header_type in ('image', 'video', 'document'):
                            components = [component_vals for component_vals in send_vals['components'] if component_vals['type'] != 'header']
                            send_vals_without_attachments['components'] = components
                        unique_message_vals = (number, frozendict(send_vals_without_attachments))
                        if unique_message_vals not in sent_message_vals:
                            sent_message_vals.add(unique_message_vals)
                        else:
                            is_duplicate = True
                    if attachment and attachment not in whatsapp_message.mail_message_id.attachment_ids:
                        # Clone the attachment to ensure the template's attachment is not affected by message changes
                        cloned_attachment = attachment.copy({'res_model': whatsapp_message.mail_message_id.model, 'res_id': whatsapp_message.mail_message_id.res_id})
                        whatsapp_message.mail_message_id.attachment_ids = [(4, cloned_attachment.id)]
                # no template
                elif whatsapp_message.mail_message_id.attachment_ids:
                    attachment_vals = whatsapp_message._prepare_attachment_vals(whatsapp_message.mail_message_id.attachment_ids[0], wa_account_id=whatsapp_message.wa_account_id)
                    message_type = attachment_vals.get('type')
                    send_vals = attachment_vals.get(message_type)
                    if whatsapp_message.body:
                        send_vals['caption'] = body
                else:
                    message_type = 'text'
                    send_vals = {
                        'preview_url': True,
                        'body': body,
                    }
                # Tagging parent message id if parent message is available
                if whatsapp_message.mail_message_id and whatsapp_message.mail_message_id.parent_id:
                    parent_id = whatsapp_message.mail_message_id.parent_id.wa_message_ids
                    if parent_id:
                        parent_message_id = parent_id[0].msg_uid
                if not is_duplicate:
                    msg_uid = wa_api._send_whatsapp(number=number, message_type=message_type, send_vals=send_vals, parent_message_id=parent_message_id)
            except WhatsAppError as we:
                whatsapp_message._handle_error(whatsapp_error_code=we.error_code, error_message=we.error_message,
                                               failure_type=we.failure_type)
            except (UserError, ValidationError) as e:
                whatsapp_message._handle_error(failure_type='unknown', error_message=str(e))
            else:
                if is_duplicate:
                    whatsapp_message.state = 'cancel'
                elif whatsapp_message.state == 'outgoing':
                    if not msg_uid:
                        whatsapp_message._handle_error(failure_type='unknown')
                    else:
                        if message_type == 'template':
                            whatsapp_message._post_message_in_active_channel()
                        whatsapp_message.write({
                            'state': 'sent',
                            'msg_uid': msg_uid
                        })
                if with_commit:
                    self._cr.commit()

    def _handle_error(self, failure_type=False, whatsapp_error_code=False, error_message=False):
        """ Format and write errors on the message. """
        self.ensure_one()
        state = 'error'
        if whatsapp_error_code:
            if whatsapp_error_code in WHATSAPP_RETRYABLE_ERROR_CODES:
                failure_type = 'whatsapp_recoverable'
            else:
                failure_type = 'whatsapp_unrecoverable'
        if not failure_type:
            failure_type = 'unknown'
        if whatsapp_error_code in BOUNCED_ERROR_CODES:
            state = 'bounced'
        self.write({
            'failure_type': failure_type,
            'failure_reason': error_message,
            'state': state,
        })

    def _post_message_in_active_channel(self):
        """ Notify the active channel that someone has sent template message. """
        self.ensure_one()
        if not self.wa_template_id:
            return
        channel = self.wa_account_id._find_active_channel(self.mobile_number_formatted)
        if not channel:
            return

        # same user, different model: print full content of message into conversation
        if channel.is_member:
            body = self.body
            message_type = "comment"
        # diffrent user from any model: warn chat is about to be moved into a new conversation
        else:
            record_name = self.mail_message_id.record_name
            if self.mail_message_id.model and self.mail_message_id.res_id:
                if not record_name:
                    record_name = self.env[self.mail_message_id.model].browse(self.mail_message_id.res_id).display_name
                url = f"{self.get_base_url()}/odoo/{self.mail_message_id.model}/{self.mail_message_id.res_id}"
                record_link = f"<a target='_blank' href='{url}'>{escape(record_name)}</a>"
            else:
                record_link = record_name or _("another document")
            body = Markup(
                _("A new template was sent on %(record_link)s.<br>"
                  "Future replies will be transferred to a new chat.",
                  record_link=record_link
            ))
            message_type = "notification"
        channel.sudo().message_post(
            body=body,
            message_type=message_type,
            subtype_xmlid='mail.mt_comment',
        )

    @api.model
    def _prepare_attachment_vals(self, attachment, wa_account_id):
        """ Upload the attachment to WhatsApp and return prepared values to attach to the message. """
        whatsapp_media_type = next((
            media_type
            for media_type, mimetypes
            in self._SUPPORTED_ATTACHMENT_TYPE.items()
            if attachment.mimetype in mimetypes),
            False
        )

        if not whatsapp_media_type:
            raise WhatsAppError(_("Attachment mimetype is not supported by WhatsApp: %s.", attachment.mimetype))
        wa_api = WhatsAppApi(wa_account_id)
        whatsapp_media_uid = wa_api._upload_whatsapp_document(attachment)

        vals = {
            'type': whatsapp_media_type,
            whatsapp_media_type: {'id': whatsapp_media_uid}
        }

        if whatsapp_media_type == 'document':
            vals[whatsapp_media_type]['filename'] = attachment.name

        return vals

    # ------------------------------------------------------------
    # CALLBACK
    # ------------------------------------------------------------

    def _process_statuses(self, value):
        """ Process status of the message like 'send', 'delivered' and 'read'."""
        mapping = {'failed': 'error', 'cancelled': 'cancel'}
        processed_message_ids = set()

        for statuses in value.get('statuses', []):
            whatsapp_message = self.env['whatsapp.message'].sudo().search([('msg_uid', '=', statuses['id'])])
            if whatsapp_message:
                whatsapp_message.state = mapping.get(statuses['status'], statuses['status'])
                processed_message_ids.add(whatsapp_message.id)
                whatsapp_message._update_message_fetched_seen()
                if statuses['status'] == 'failed':
                    error = statuses['errors'][0] if statuses.get('errors') else None
                    if error:
                        whatsapp_message._handle_error(whatsapp_error_code=error['code'],
                                                          error_message=f"{error['code']} : {error['title']}")
        return self.env['whatsapp.message'].browse(sorted(processed_message_ids, reverse=True)).sudo()

    def _update_message_fetched_seen(self):
        """ Update message status for the whatsapp recipient. """
        self.ensure_one()
        if self.mail_message_id.model != 'discuss.channel':
            return
        channel = self.env['discuss.channel'].browse(self.mail_message_id.res_id)
        channel_member = channel.channel_member_ids.filtered(lambda cm: cm.partner_id == channel.whatsapp_partner_id)
        if not channel_member:
            return
        channel_member = channel_member[0]
        notification_type = None
        if self.state == 'read':
            channel_member.write({
                'fetched_message_id': max(channel_member.fetched_message_id.id, self.mail_message_id.id),
                'seen_message_id': self.mail_message_id.id,
                'last_seen_dt': fields.Datetime.now(),
            })
            notification_type = 'discuss.channel.member/seen'
        elif self.state == 'delivered':
            channel_member.write({'fetched_message_id': self.mail_message_id.id})
            notification_type = 'discuss.channel.member/fetched'
        if notification_type:
            channel._bus_send(
                notification_type,
                {
                    "channel_id": channel.id,
                    "id": channel_member.id,
                    "last_message_id": self.mail_message_id.id,
                    "partner_id": channel.whatsapp_partner_id.id,
                },
            )
