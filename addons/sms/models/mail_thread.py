# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, Command, models, fields
from odoo.addons.sms.tools.sms_tools import sms_content_to_rendered_html
from odoo.tools import html2plaintext

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    message_has_sms_error = fields.Boolean(
        'SMS Delivery error', compute='_compute_message_has_sms_error', search='_search_message_has_sms_error',
        help="If checked, some messages have a delivery error.")

    def _compute_message_has_sms_error(self):
        res = {}
        if self.ids:
            self.env.cr.execute("""
                    SELECT msg.res_id, COUNT(msg.res_id)
                      FROM mail_message msg
                INNER JOIN mail_notification notif
                        ON notif.mail_message_id = msg.id
                     WHERE notif.notification_type = 'sms'
                       AND notif.notification_status = 'exception'
                       AND notif.author_id = %(author_id)s
                       AND msg.model = %(model_name)s
                       AND msg.res_id in %(res_ids)s
                       AND msg.message_type != 'user_notification'
                  GROUP BY msg.res_id
            """, {'author_id': self.env.user.partner_id.id, 'model_name': self._name, 'res_ids': tuple(self.ids)})
            res.update(self.env.cr.fetchall())

        for record in self:
            record.message_has_sms_error = bool(res.get(record._origin.id, 0))

    @api.model
    def _search_message_has_sms_error(self, operator, operand):
        if operator != 'in':
            return NotImplemented
        return ['&', ('message_ids.has_sms_error', '=', True), ('message_ids.author_id', '=', self.env.user.partner_id.id)]

    def message_post(self, *args, body='', message_type='notification', **kwargs):
        # When posting an 'SMS' `message_type`, make sure that the body is used as-is in the sms,
        # and reformat the message body for the notification (mainly making URLs clickable).
        if message_type == 'sms':
            kwargs['sms_content'] = body
            body = sms_content_to_rendered_html(body)
        return super().message_post(*args, body=body, message_type=message_type, **kwargs)

    def _message_sms_schedule_mass(self, body='', template=False, **composer_values):
        """ Shortcut method to schedule a mass sms sending on a recordset.

        :param template: an optional sms.template record;
        """
        composer_context = {
            'default_res_model': self._name,
            'default_composition_mode': 'mass',
            'default_template_id': template.id if template else False,
            'default_res_ids': self.ids,
        }
        if body and not template:
            composer_context['default_body'] = body

        create_vals = {
            'mass_force_send': False,
            'mass_keep_log': True,
        }
        if composer_values:
            create_vals.update(composer_values)

        composer = self.env['sms.composer'].with_context(**composer_context).create(create_vals)
        return composer._action_send_sms()

    def _message_sms_with_template(self, template=False, template_xmlid=False, template_fallback='', partner_ids=False, **kwargs):
        """ Shortcut method to perform a _message_sms with an sms.template.

        :param template: a valid sms.template record;
        :param template_xmlid: XML ID of an sms.template (if no template given);
        :param template_fallback: plaintext (inline_template-enabled) in case template
          and template xml id are falsy (for example due to deleted data);
        """
        self.ensure_one()
        if not template and template_xmlid:
            template = self.env.ref(template_xmlid, raise_if_not_found=False)
        if template:
            body = template._render_field('body', self.ids, compute_lang=True)[self.id]
        else:
            body = self.env['sms.template']._render_template(template_fallback, self._name, self.ids)[self.id]
        return self._message_sms(body, partner_ids=partner_ids, **kwargs)

    def _message_sms(self, body, subtype_id=False, partner_ids=False, number_field=False,
                     sms_numbers=None, sms_pid_to_number=None, **kwargs):
        """ Main method to post a message on a record using SMS-based notification
        method.

        :param body: content of SMS;
        :param subtype_id: mail.message.subtype used in mail.message associated
          to the sms notification process;
        :param partner_ids: if set is a record set of partners to notify;
        :param number_field: if set is a name of field to use on current record
          to compute a number to notify;
        :param sms_numbers: see ``_notify_thread_by_sms``;
        :param sms_pid_to_number: see ``_notify_thread_by_sms``;
        """
        self.ensure_one()
        sms_pid_to_number = sms_pid_to_number if sms_pid_to_number is not None else {}

        if number_field or (partner_ids is False and sms_numbers is None):
            info = self._sms_get_recipients_info(force_field=number_field)[self.id]
            info_partner_ids = info['partner'].ids if info['partner'] else False
            info_number = info['sanitized'] if info['sanitized'] else info['number']
            if info_partner_ids and info_number:
                sms_pid_to_number[info_partner_ids[0]] = info_number
            if info_partner_ids:
                partner_ids = info_partner_ids + (partner_ids or [])
            if not info_partner_ids:
                if info_number:
                    sms_numbers = [info_number] + (sms_numbers or [])
                    # will send a falsy notification allowing to fix it through SMS wizards
                elif not sms_numbers:
                    sms_numbers = [False]

        if subtype_id is False:
            subtype_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note')

        return self.message_post(
            body=body, partner_ids=partner_ids or [],  # TDE FIXME: temp fix otherwise crash mail_thread.py
            message_type='sms', subtype_id=subtype_id,
            sms_numbers=sms_numbers, sms_pid_to_number=sms_pid_to_number,
            **kwargs
        )

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        # Main notification method. Override to add support of sending SMS notifications.
        scheduled_date = self._is_notification_scheduled(kwargs.get('scheduled_date'))
        recipients_data = super()._notify_thread(message, msg_vals=msg_vals, **kwargs)
        if not scheduled_date:
            self._notify_thread_by_sms(message, recipients_data, msg_vals=msg_vals, **kwargs)
        return recipients_data

    def _notify_thread_by_sms(self, message, recipients_data, msg_vals=False,
                              sms_content=None, sms_numbers=None, sms_pid_to_number=None,
                              put_in_queue=False, **kwargs):
        """ Notification method: by SMS.

        :param record message: <mail.message> record being notified. May be
          void as 'msg_vals' superseeds it;
        :param list recipients_data: list of recipients data based on <res.partner>
          records formatted like a list of dicts containing information. See
          ``MailThread._notify_get_recipients()``;
        :param dict msg_vals: values dict used to create the message, allows to
          skip message usage and spare some queries if given;

        :param sms_content: plaintext version of body, mainly to avoid
          conversion glitches by splitting html and plain text content formatting
          (e.g.: links, styling.).
          If not given, `msg_vals`'s `body` is used and converted from html to plaintext;
        :param sms_numbers: additional numbers to notify in addition to partners
          and classic recipients;
        :param sms_pid_to_number: force a number to notify for a given partner ID
          instead of taking its mobile / phone number;
        :param put_in_queue: use cron to send queued SMS instead of sending them
          directly;
        """
        msg_vals = msg_vals or {}
        sms_pid_to_number = sms_pid_to_number if sms_pid_to_number is not None else {}
        sms_numbers = sms_numbers if sms_numbers is not None else []
        sms_create_vals = []
        sms_all = self.env['sms.sms'].sudo()

        # pre-compute SMS data
        body = sms_content or html2plaintext(msg_vals['body'] if 'body' in msg_vals else message.body)
        sms_base_vals = {
            'body': body,
            'mail_message_id': message.id,
            'state': 'outgoing',
        }

        # notify from computed recipients_data (followers, specific recipients)
        partners_data = [r for r in recipients_data if r['notif'] == 'sms']
        partner_ids = [r['id'] for r in partners_data]
        if partner_ids:
            for partner in self.env['res.partner'].sudo().browse(partner_ids):
                number = sms_pid_to_number.get(partner.id) or partner.phone
                sms_create_vals.append(dict(
                    sms_base_vals,
                    partner_id=partner.id,
                    number=partner._phone_format(number=number) or number,
                ))

        # notify from additional numbers
        if sms_numbers:
            tocreate_numbers = [
                self._phone_format(number=sms_number) or sms_number
                for sms_number in sms_numbers
            ]
            existing_partners_numbers = {vals_dict['number'] for vals_dict in sms_create_vals}
            sms_create_vals += [dict(
                sms_base_vals,
                partner_id=False,
                number=n,
                state='outgoing' if n else 'error',
                failure_type='' if n else 'sms_number_missing',
            ) for n in tocreate_numbers if n not in existing_partners_numbers]

        # create sms and notification
        if sms_create_vals:
            sms_all |= self.env['sms.sms'].sudo().create(sms_create_vals)

            notif_create_values = [{
                'author_id': message.author_id.id,
                'mail_message_id': message.id,
                'res_partner_id': sms.partner_id.id,
                'sms_number': sms.number,
                'notification_type': 'sms',
                'sms_id_int': sms.id,
                'sms_tracker_ids': [Command.create({'sms_uuid': sms.uuid})] if sms.state == 'outgoing' else False,
                'is_read': True,  # discard Inbox notification
                'notification_status': 'ready' if sms.state == 'outgoing' else 'exception',
                'failure_type': '' if sms.state == 'outgoing' else sms.failure_type,
            } for sms in sms_all]
            if notif_create_values:
                self.env['mail.notification'].sudo().create(notif_create_values)

        if sms_all and not put_in_queue:
            sms_all.filtered(lambda sms: sms.state == 'outgoing').send(raise_exception=False)

        return True

    def _get_notify_valid_parameters(self):
        return super()._get_notify_valid_parameters() | {
            'put_in_queue', 'sms_numbers', 'sms_pid_to_number', 'sms_content',
        }

    @api.model
    def notify_cancel_by_type(self, notification_type):
        super().notify_cancel_by_type(notification_type)
        if notification_type == 'sms':
            # TDE CHECK: delete pending SMS
            self._notify_cancel_by_type_generic('sms')
        return True
