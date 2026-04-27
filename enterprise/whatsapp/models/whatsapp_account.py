# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import mimetypes
import secrets
import string
from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.whatsapp.tools.whatsapp_api import WhatsAppApi
from odoo.addons.whatsapp.tools.whatsapp_exception import WhatsAppError
from odoo.tools import plaintext2html

_logger = logging.getLogger(__name__)


class WhatsAppAccount(models.Model):
    _name = 'whatsapp.account'
    _inherit = ['mail.thread']
    _description = 'WhatsApp Business Account'

    name = fields.Char(string="Name", tracking=1)
    active = fields.Boolean(default=True, tracking=6)

    app_uid = fields.Char(string="App ID", required=True, tracking=2)
    app_secret = fields.Char(string="App Secret", groups='whatsapp.group_whatsapp_admin', required=True)
    account_uid = fields.Char(string="Account ID", required=True, tracking=3)
    phone_uid = fields.Char(string="Phone Number ID", required=True, tracking=4)
    token = fields.Char(string="Access Token", required=True, groups='whatsapp.group_whatsapp_admin')
    webhook_verify_token = fields.Char(string="Webhook Verify Token", compute='_compute_verify_token',
                                       groups='whatsapp.group_whatsapp_admin', store=True)
    callback_url = fields.Char(string="Callback URL", compute='_compute_callback_url', readonly=True, copy=False)

    allowed_company_ids = fields.Many2many(
        comodel_name='res.company', string="Allowed Company",
        default=lambda self: self.env.company)
    notify_user_ids = fields.Many2many(
        comodel_name='res.users', default=lambda self: self.env.user,
        domain=[('share', '=', False)], required=True, tracking=5,
        help="Users to notify when a message is received and there is no template send in last 15 days")

    templates_count = fields.Integer(string="Message Count", compute='_compute_templates_count')

    _sql_constraints = [
        ('phone_uid_unique', 'unique(phone_uid)', "The same phone number ID already exists")]

    @api.constrains('notify_user_ids')
    def _check_notify_user_ids(self):
        for phone in self:
            if len(phone.notify_user_ids) < 1:
                raise ValidationError(_("Users to notify is required"))

    def _compute_callback_url(self):
        for account in self:
            account.callback_url = self.get_base_url() + '/whatsapp/webhook'

    @api.depends('account_uid')
    def _compute_verify_token(self):
        """ webhook_verify_token only set when record is created. Not update after that."""
        for rec in self:
            if rec.id and not rec.webhook_verify_token:
                rec.webhook_verify_token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))

    def _compute_templates_count(self):
        for tmpl in self:
            tmpl.templates_count = self.env['whatsapp.template'].search_count([('wa_account_id', '=', tmpl.id)])

    def button_sync_whatsapp_account_templates(self):
        """
            This method will sync all the templates of the WhatsApp Business Account.
            It will create new templates and update existing templates.
        """
        self.ensure_one()
        try:
            response = WhatsAppApi(self)._get_all_template(fetch_all=True)
        except WhatsAppError as err:
            raise ValidationError(str(err)) from err

        WhatsappTemplate = self.env['whatsapp.template']
        existing_tmpls = WhatsappTemplate.with_context(active_test=False).search([('wa_account_id', '=', self.id)])
        existing_tmpl_by_id = {t.wa_template_uid: t for t in existing_tmpls}
        template_update_count = 0
        template_create_count = 0
        if response.get('data'):
            create_vals = []
            for template in response['data']:
                existing_tmpl = existing_tmpl_by_id.get(template['id'])
                if existing_tmpl:
                    template_update_count += 1
                    existing_tmpl._update_template_from_response(template)
                else:
                    template_create_count += 1
                    create_vals.append(WhatsappTemplate._create_template_from_response(template, self))
            WhatsappTemplate.create(create_vals)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Templates synchronized!"),
                'type': 'success',
                'message': _("%(create_count)s were created, %(update_count)s were updated",
                    create_count=template_create_count, update_count=template_update_count),
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def button_test_connection(self):
        """ Test connection of the WhatsApp Business Account. with the given credentials.
        """
        self.ensure_one()
        wa_api = WhatsAppApi(self)
        try:
            wa_api._test_connection()
        except WhatsAppError as e:
            raise UserError(str(e))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _("Credentials look good!"),
            }
        }

    def action_open_templates(self):
        self.ensure_one()
        return {
            'name': _("Templates Of %(account_name)s", account_name=self.name),
            'view_mode': 'list,form',
            'res_model': 'whatsapp.template',
            'domain': [('wa_account_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'context': {'default_wa_account_id': self.id},
        }

    def _find_active_channel(self, sender_mobile_formatted, sender_name=False, create_if_not_found=False):
        """This method will find the active channel for the given sender mobile number."""
        self.ensure_one()
        whatsapp_message = self.env['whatsapp.message'].sudo().search(
            [
                ('mobile_number_formatted', '=', sender_mobile_formatted),
                ('wa_account_id', '=', self.id),
                ('wa_template_id', '!=', False),
                ('state', 'not in', ['outgoing', 'error', 'cancel']),
            ], limit=1, order='id desc')
        return self.env['discuss.channel'].sudo()._get_whatsapp_channel(
            whatsapp_number=sender_mobile_formatted or '',
            wa_account_id=self,
            sender_name=sender_name,
            create_if_not_found=create_if_not_found,
            related_message=whatsapp_message.mail_message_id,
        )

    def _process_messages(self, value):
        """
            This method is used for processing messages with the values received via webhook.
            If any whatsapp message template has been sent from this account then it will find the active channel or
            create new channel with last template message sent to that number and post message in that channel.
            And if channel is not found then it will create new channel with notify user set in account and post message.
            Supported Messages
             => Text Message
             => Attachment Message with caption
             => Location Message
             => Contact Message
             => Message Reactions
        """
        if 'messages' not in value and value.get('whatsapp_business_api_data', {}).get('messages'):
            value = value['whatsapp_business_api_data']

        wa_api = WhatsAppApi(self)

        for messages in value.get('messages', []):
            parent_msg_id = False
            parent_id = False
            channel = False
            sender_name = value.get('contacts', [{}])[0].get('profile', {}).get('name')
            sender_mobile = messages['from']
            message_type = messages['type']
            if 'context' in messages and messages['context'].get('id'):
                parent_whatsapp_message = self.env['whatsapp.message'].sudo().search([('msg_uid', '=', messages['context']['id'])])
                if parent_whatsapp_message:
                    parent_msg_id = parent_whatsapp_message.id
                    parent_id = parent_whatsapp_message.mail_message_id
                if parent_id:
                    channel = self.env['discuss.channel'].sudo().search([('message_ids', 'in', parent_id.id)], limit=1)

            if not channel:
                channel = self._find_active_channel(sender_mobile, sender_name=sender_name, create_if_not_found=True)
            kwargs = {
                'message_type': 'whatsapp_message',
                'author_id': channel.whatsapp_partner_id.id,
                'parent_msg_id': parent_msg_id,
                'subtype_xmlid': 'mail.mt_comment',
                'parent_id': parent_id.id if parent_id else None,
            }
            if message_type == 'text':
                kwargs['body'] = plaintext2html(messages['text']['body'])
            elif message_type == 'button':
                kwargs['body'] = messages['button']['text']
            elif message_type in ('document', 'image', 'audio', 'video', 'sticker'):
                filename = messages[message_type].get('filename')
                is_voice = messages[message_type].get('voice')
                mime_type = messages[message_type].get('mime_type')
                caption = messages[message_type].get('caption')
                datas = wa_api._get_whatsapp_document(messages[message_type]['id'])
                if not filename:
                    extension = mimetypes.guess_extension(mime_type) or ''
                    filename = message_type + extension
                kwargs['attachments'] = [(filename, datas, {'voice': is_voice})]
                if caption:
                    kwargs['body'] = plaintext2html(caption)
            elif message_type == 'location':
                url = Markup("https://maps.google.com/maps?q={latitude},{longitude}").format(
                    latitude=messages['location']['latitude'], longitude=messages['location']['longitude'])
                body = Markup('<a target="_blank" href="{url}"> <i class="fa fa-map-marker"/> {location_string} </a>').format(
                    url=url, location_string=_("Location"))
                if messages['location'].get('name'):
                    body += Markup("<br/>{location_name}").format(location_name=messages['location']['name'])
                if messages['location'].get('address'):
                    body += Markup("<br/>{location_address}").format(location_address=messages['location']['address'])
                kwargs['body'] = body
            elif message_type == 'contacts':
                body = ""
                for contact in messages['contacts']:
                    body += Markup("<i class='fa fa-address-book'/> {contact_name} <br/>").format(
                        contact_name=contact.get('name', {}).get('formatted_name', ''))
                    for phone in contact.get('phones'):
                        body += Markup("{phone_type}: {phone_number}<br/>").format(
                            phone_type=phone.get('type'), phone_number=phone.get('phone'))
                kwargs['body'] = body
            elif message_type == 'reaction':
                msg_uid = messages['reaction'].get('message_id')
                whatsapp_message = self.env['whatsapp.message'].sudo().search([('msg_uid', '=', msg_uid)])
                if whatsapp_message:
                    partner_id = channel.whatsapp_partner_id
                    emoji = messages['reaction'].get('emoji')
                    whatsapp_message.mail_message_id._post_whatsapp_reaction(reaction_content=emoji, partner_id=partner_id)
                    continue
            else:
                _logger.warning("Unsupported whatsapp message type: %s", messages)
                continue
            channel.message_post(whatsapp_inbound_msg_uid=messages['id'], **kwargs)
