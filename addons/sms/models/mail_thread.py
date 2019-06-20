# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, models, fields
from odoo.addons.phone_validation.tools import phone_validation
from odoo.tools import html2plaintext

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    message_has_sms_error = fields.Boolean(
        'SMS Delivery error', compute='_compute_message_has_sms_error', search='_search_message_has_sms_error',
        help="If checked, some messages have a delivery error.")

    @api.multi
    def _compute_message_has_sms_error(self):
        res = {}
        if self.ids:
            self._cr.execute(""" SELECT msg.res_id, COUNT(msg.res_id) FROM mail_message msg
                                 RIGHT JOIN mail_message_res_partner_needaction_rel rel
                                 ON rel.mail_message_id = msg.id AND rel.notification_type = 'sms' AND rel.notification_status in ('exception')
                                 WHERE msg.author_id = %s AND msg.model = %s AND msg.res_id in %s AND msg.message_type != 'user_notification'
                                 GROUP BY msg.res_id""",
                             (self.env.user.partner_id.id, self._name, tuple(self.ids),))
            res.update(self._cr.fetchall())

        for record in self:
            record.message_has_sms_error = bool(res.get(record._origin.id, 0))

    @api.model
    def _search_message_has_sms_error(self, operator, operand):
        return ['&', ('message_ids.has_sms_error', operator, operand), ('message_ids.author_id', '=', self.env.user.partner_id.id)]

    def _sms_get_default_partners(self):
        """ This method will likely need to be overriden by inherited models.
               :returns partners: recordset of res.partner
        """
        partners = self.env['res.partner']
        if hasattr(self, 'partner_id'):
            partners |= self.mapped('partner_id')
        if hasattr(self, 'partner_ids'):
            partners |= self.mapped('partner_ids')
        return partners

    def _sms_get_number_fields(self):
        """ This method returns the fields to use to find the number to use to
        send an SMS on a record. """
        return ['mobile']

    def _sms_get_recipients_info(self, force_field=False):
        """" Get SMS recipient information on current record set. This method
        checks for numbers and sanitization in order to centralize computation.

        Exmaple of use cases

          * click on a field -> number forced from field, find customer, force its number to field or fallback
            on customer fields;
          * contact -> find numbers from field, find customer, force its number to field or fallback
            on custome fields;
        """
        result = dict.fromkeys(self.ids, False)
        number_fields = self._sms_get_number_fields()
        for record in self:
            tocheck_fields = [force_field] if force_field else number_fields
            all_numbers = [record[fname] for fname in tocheck_fields if fname in record]
            all_partners = record._sms_get_default_partners()

            valid_number = False
            for fname in [f for f in tocheck_fields if f in record]:
                valid_number = phone_validation.phone_get_sanitized_record_number(record, number_fname=fname)
                if valid_number:
                    break

            if valid_number:
                result[record.id] = {
                    'partner': all_partners[0] if all_partners else self.env['res.partner'],
                    'sanitized': valid_number, 'number': valid_number,
                }
            elif all_partners:
                partner_number, partner = False, self.env['res.partner']
                for partner in all_partners:
                    partner_number = partner.mobile or partner.phone
                    if partner_number:
                        partner_number = phone_validation.phone_sanitize_numbers_string_w_record(partner_number, record)[partner_number]['sanitized']
                    if partner_number:
                        break

                if partner_number:
                    result[record.id] = {'partner': partner, 'sanitized': partner_number, 'number': partner_number}
                else:
                    result[record.id] = {'partner': partner, 'sanitized': False, 'number': partner.mobile or partner.phone}
            elif all_numbers:
                result[record.id] = {'partner': self.env['res.partner'], 'sanitized': False, 'number': all_numbers[0]}
            else:
                result[record.id] = {'partner': self.env['res.partner'], 'sanitized': False, 'number': False}
        return result

    def _message_sms_schedule_mass(self, body='', template=False, active_domain=None):
        composer_context = {
            'default_res_model': self._name,
            'default_composition_mode': 'mass',
            'default_template_id': template.id if template else False,
            'default_body': body if body and not template else False,
        }
        if active_domain is not None:
            composer_context['default_use_active_domain'] = True
            composer_context['default_active_domain'] = repr(active_domain)
        else:
            composer_context['default_res_ids'] = self.ids

        composer = self.env['sms.composer'].with_context(**composer_context).create({})
        return composer._action_send_sms()

    def _message_sms_with_template(self, template_xmlid=False, template=False, template_fallback='', partner_ids=False, put_in_queue=False):
        self.ensure_one()
        if not template and template_xmlid:
            template = self.env.ref(template_xmlid, raise_if_not_found=False)
        if template:
            template_w_lang = template._set_context_lang(self.ids)[self.id]
            body = template._render_template(template_w_lang.body, self._name, self.ids)[self.id]
        else:
            body = self.env['sms.template']._render_template(template_fallback, self._name, self.ids)[self.id]
        return self._message_sms(body, partner_ids=partner_ids)

    def _message_sms(self, body, subtype_id=False, partner_ids=False, number_field=False, numbers=False):
        """ Main method to post a message on a record using SMS-based notification
        method.

        :param body: content of SMS;
        :param subtype_id: mail.message.subtype used in mail.message associated
          to the sms notification process;
        :param partner_ids: if set is a record set of partners to notify;
        :param number_field: if set is a name of field to use on current record
          to compute a number to notify;
        :param numbers: if set is a list of phone numbers to notify;
        """
        self.ensure_one()

        if number_field or (partner_ids is False and numbers is False):
            info = self._sms_get_recipients_info(force_field=number_field)[self.id]
            info_partner_ids = info['partner'].ids if info['partner'] else False
            info_number = info['sanitized'] if info['sanitized'] else info['number']
            if info_partner_ids and info_number:
                pid_to_number = self.env.context.get('notify_sms_pid_to_number', {})
                pid_to_number[info_partner_ids[0]] = info_number
                self = self.with_context(notify_sms_pid_to_number=pid_to_number)
            if info_partner_ids:
                partner_ids = info_partner_ids + (partner_ids or [])
            if info_number and not info_partner_ids:
                numbers = [info_number] + (numbers or [])

        if numbers:
            self = self.with_context(notify_sms_numbers=numbers)

        if subtype_id is False:
            subtype_id = self.env['ir.model.data'].xmlid_to_res_id('mail.mt_comment')

        return self.message_post(
            body=body, partner_ids=partner_ids or [],  # TDE FIXME: temp fix otherwise crash mail_thread.py
            message_type='sms', subtype_id=subtype_id,
        )

    @api.multi
    def _notify_thread(self, message, msg_vals=False, model_description=False, mail_auto_delete=True):
        recipients_data = super(MailThread, self)._notify_thread(
            message, msg_vals=msg_vals, model_description=model_description,
            mail_auto_delete=mail_auto_delete,
        )
        self._notify_records_by_sms(message, recipients_data, msg_vals=msg_vals, put_in_queue=False)
        return recipients_data

    @api.multi
    def _notify_records_by_sms(self, message, recipients_data, msg_vals=False, put_in_queue=False):
        """ Notification method: by SMS. Some specific context keys allow to customize
        the process:

          * notify_check_existing: check existing notifications to update instead
              of creating new one (allow to speedup classic post by always creating
              new one);
          * notify_sms_pid_to_number: force a number to notify for a given partner ID
              instead of taking its mobile / phone number;
          * notify_sms_numbers: additional numbers to notify;
        """
        notify_check_existing = self.env.context.get('notify_check_existing', False)
        pid_to_number = self.env.context.get('notify_sms_pid_to_number', {})
        numbers = self.env.context.get('notify_sms_numbers', [])
        sms_create_vals = []
        sms_all = self.env['sms.sms'].sudo()

        # pre-compute SMS data
        body = msg_vals['body'] if msg_vals and msg_vals.get('body') else message.body
        sms_base_vals = {
            'body': html2plaintext(body).rstrip('\n'),
            'mail_message_id': message.id,
            'state': 'outgoing',
        }

        # notify from computed recipients_data (followers, specific recipients)
        partners_data = [r for r in recipients_data['partners'] if r['notif'] == 'sms']
        partner_ids = [r['id'] for r in partners_data]
        if partner_ids:
            for partner in self.env['res.partner'].sudo().browse(partner_ids):
                number = pid_to_number.get(partner.id) or partner.mobile or partner.phone
                sanitize_res = phone_validation.phone_sanitize_numbers_string_w_record(number, partner)[number]
                number = sanitize_res['sanitized'] or number
                sms_create_vals.append(dict(
                    sms_base_vals,
                    partner_id=partner.id,
                    number=number
                ))

        # notify from additional numbers
        if numbers:
            sanitized = phone_validation.phone_sanitize_numbers_w_record(numbers, self)
            tocreate_numbers = [
                value['sanitized'] or original
                for original, value in sanitized.items()
                if value['code'] != 'empty'
            ]
            sms_create_vals += [dict(sms_base_vals, partner_id=False, number=n) for n in tocreate_numbers]

        # create sms and notification
        existing_pids, existing_numbers = [], []
        if sms_create_vals:
            sms_all |= self.env['sms.sms'].sudo().create(sms_create_vals)

            if notify_check_existing:
                existing = self.env['mail.notification'].sudo().search([
                    '|', ('res_partner_id', 'in', partner_ids),
                    '&', ('res_partner_id', '=', False), ('sms_number', 'in', numbers),
                    ('notification_type', '=', 'sms'),
                    ('mail_message_id', '=', message.id)
                ])
                for n in existing:
                    if n.res_partner_id.id in partner_ids and n.mail_message_id == message:
                        existing_pids.append(n.res_partner_id.id)
                    if not n.res_partner_id and n.sms_number in numbers and n.mail_message_id == message:
                        existing_numbers.append(n.sms_number)

            notif_create_values = [{
                'mail_message_id': message.id,
                'res_partner_id': sms.partner_id.id,
                'sms_number': sms.number,
                'notification_type': 'sms',
                'sms_id': sms.id,
                'is_read': True,  # discard Inbox notification
                'notification_status': 'ready',
            } for sms in sms_all if (sms.partner_id and sms.partner_id.id not in existing_pids) or (not sms.partner_id and sms.number not in existing_numbers)]
            if notif_create_values:
                self.env['mail.notification'].sudo().create(notif_create_values)

            if existing_pids or existing_numbers:
                for sms in sms_all:
                    notif = next((n for n in existing if
                                 (n.res_partner_id.id in existing_pids and n.res_partner_id.id == sms.partner_id.id) or
                                 (not n.res_partner_id and n.sms_number in existing_numbers and n.sms_number == sms.number)), False)
                    # notif = existing.filtered(lambda n: n.res_partner_id.id in existing_pids or (not n.res_partner_id and n.sms_number in existing_numbers))
                    if notif:
                        notif.write({
                            'notification_type': 'sms',
                            'notification_status': 'ready',
                            'sms_id': sms.id,
                            'sms_number': sms.number,
                        })

        if sms_all and not put_in_queue:
            sms_all.send(auto_commit=False, raise_exception=False)

        return True
