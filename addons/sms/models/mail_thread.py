# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, Command, models, fields
from odoo.tools import html2plaintext, plaintext2html

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
            res.update(self._cr.fetchall())

        for record in self:
            record.message_has_sms_error = bool(res.get(record._origin.id, 0))

    @api.model
    def _search_message_has_sms_error(self, operator, operand):
        return ['&', ('message_ids.has_sms_error', operator, operand), ('message_ids.author_id', '=', self.env.user.partner_id.id)]

    def _sms_get_recipients_info(self, force_field=False, partner_fallback=True):
        """" Get SMS recipient information on current record set. This method
        checks for numbers and sanitation in order to centralize computation.

        Example of use cases

          * click on a field -> number is actually forced from field, find customer
            linked to record, force its number to field or fallback on customer fields;
          * contact -> find numbers from all possible phone fields on record, find
            customer, force its number to found field number or fallback on customer fields;

        :param force_field: either give a specific field to find phone number, either
            generic heuristic is used to find one based on ``_phone_get_number_fields``;
        :param partner_fallback: if no value found in the record, check its customer
            values based on ``_mail_get_partners``;

        :return dict: record.id: {
            'partner': a res.partner recordset that is the customer (void or singleton)
                linked to the recipient. See ``_mail_get_partners``;
            'sanitized': sanitized number to use (coming from record's field or partner's
                phone fields). Set to False is number impossible to parse and format;
            'number': original number before sanitation;
            'partner_store': whether the number comes from the customer phone fields. If
                False it means number comes from the record itself, even if linked to a
                customer;
            'field_store': field in which the number has been found (generally mobile or
                phone, see ``_phone_get_number_fields``);
        } for each record in self
        """
        result = dict.fromkeys(self.ids, False)
        tocheck_fields = [force_field] if force_field else self._phone_get_number_fields()
        for record in self:
            all_numbers = [record[fname] for fname in tocheck_fields if fname in record]
            all_partners = record._mail_get_partners()[record.id]

            valid_number, fname = False, False
            for fname in [f for f in tocheck_fields if f in record]:
                valid_number = record._phone_format(fname=fname)
                if valid_number:
                    break

            if valid_number:
                result[record.id] = {
                    'partner': all_partners[0] if all_partners else self.env['res.partner'],
                    'sanitized': valid_number,
                    'number': record[fname],
                    'partner_store': False,
                    'field_store': fname,
                }
            elif all_partners and partner_fallback:
                partner = self.env['res.partner']
                for partner in all_partners:
                    for fname in self.env['res.partner']._phone_get_number_fields():
                        valid_number = partner._phone_format(fname=fname)
                        if valid_number:
                            break

                if not valid_number:
                    fname = 'mobile' if partner.mobile else ('phone' if partner.phone else 'mobile')

                result[record.id] = {
                    'partner': partner,
                    'sanitized': valid_number if valid_number else False,
                    'number': partner[fname],
                    'partner_store': True,
                    'field_store': fname,
                }
            else:
                # did not find any sanitized number -> take first set value as fallback;
                # if none, just assign False to the first available number field
                value, fname = next(
                    ((value, fname) for value, fname in zip(all_numbers, tocheck_fields) if value),
                    (False, tocheck_fields[0] if tocheck_fields else False)
                )
                result[record.id] = {
                    'partner': self.env['res.partner'],
                    'sanitized': False,
                    'number': value,
                    'partner_store': False,
                    'field_store': fname
                }
        return result

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
            body=plaintext2html(html2plaintext(body)), partner_ids=partner_ids or [],  # TDE FIXME: temp fix otherwise crash mail_thread.py
            message_type='sms', subtype_id=subtype_id,
            sms_numbers=sms_numbers, sms_pid_to_number=sms_pid_to_number,
            **kwargs
        )

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        scheduled_date = self._is_notification_scheduled(kwargs.get('scheduled_date'))
        recipients_data = super(MailThread, self)._notify_thread(message, msg_vals=msg_vals, **kwargs)
        if not scheduled_date:
            self._notify_thread_by_sms(message, recipients_data, msg_vals=msg_vals, **kwargs)
        return recipients_data

    def _notify_thread_by_sms(self, message, recipients_data, msg_vals=False,
                              sms_numbers=None, sms_pid_to_number=None,
                              resend_existing=False, put_in_queue=False, **kwargs):
        """ Notification method: by SMS.

        :param message: ``mail.message`` record to notify;
        :param recipients_data: list of recipients information (based on res.partner
          records), formatted like
            [{'active': partner.active;
              'id': id of the res.partner being recipient to notify;
              'groups': res.group IDs if linked to a user;
              'notif': 'inbox', 'email', 'sms' (SMS App);
              'share': partner.partner_share;
              'type': 'customer', 'portal', 'user;'
             }, {...}].
          See ``MailThread._notify_get_recipients``;
        :param msg_vals: dictionary of values used to create the message. If given it
          may be used to access values related to ``message`` without accessing it
          directly. It lessens query count in some optimized use cases by avoiding
          access message content in db;

        :param sms_numbers: additional numbers to notify in addition to partners
          and classic recipients;
        :param pid_to_number: force a number to notify for a given partner ID
              instead of taking its mobile / phone number;
        :param resend_existing: check for existing notifications to update based on
          mailed recipient, otherwise create new notifications;
        :param put_in_queue: use cron to send queued SMS instead of sending them
          directly;
        """
        sms_pid_to_number = sms_pid_to_number if sms_pid_to_number is not None else {}
        sms_numbers = sms_numbers if sms_numbers is not None else []
        sms_create_vals = []
        sms_all = self.env['sms.sms'].sudo()

        # pre-compute SMS data
        body = msg_vals['body'] if msg_vals and 'body' in msg_vals else message.body
        sms_base_vals = {
            'body': html2plaintext(body),
            'mail_message_id': message.id,
            'state': 'outgoing',
        }

        # notify from computed recipients_data (followers, specific recipients)
        partners_data = [r for r in recipients_data if r['notif'] == 'sms']
        partner_ids = [r['id'] for r in partners_data]
        if partner_ids:
            for partner in self.env['res.partner'].sudo().browse(partner_ids):
                number = sms_pid_to_number.get(partner.id) or partner.mobile or partner.phone
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
        existing_pids, existing_numbers = [], []
        if sms_create_vals:
            sms_all |= self.env['sms.sms'].sudo().create(sms_create_vals)

            if resend_existing:
                existing = self.env['mail.notification'].sudo().search([
                    '|', ('res_partner_id', 'in', partner_ids),
                    '&', ('res_partner_id', '=', False), ('sms_number', 'in', sms_numbers),
                    ('notification_type', '=', 'sms'),
                    ('mail_message_id', 'in', message.ids),
                ])
                for n in existing:
                    if n.res_partner_id.id in partner_ids and n.mail_message_id == message:
                        existing_pids.append(n.res_partner_id.id)
                    if not n.res_partner_id and n.sms_number in sms_numbers and n.mail_message_id == message:
                        existing_numbers.append(n.sms_number)

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
            } for sms in sms_all if (sms.partner_id and sms.partner_id.id not in existing_pids) or (not sms.partner_id and sms.number not in existing_numbers)]
            if notif_create_values:
                self.env['mail.notification'].sudo().create(notif_create_values)

            if existing_pids or existing_numbers:
                for sms in sms_all:
                    notif = next((n for n in existing if
                                 (n.res_partner_id.id in existing_pids and n.res_partner_id.id == sms.partner_id.id) or
                                 (not n.res_partner_id and n.sms_number in existing_numbers and n.sms_number == sms.number)), False)
                    if notif:
                        notif.write({
                            'notification_type': 'sms',
                            'notification_status': 'ready',
                            'sms_id_int': sms.id,
                            'sms_tracker_ids': [Command.create({'sms_uuid': sms.uuid})],
                            'sms_number': sms.number,
                        })

        if sms_all and not put_in_queue:
            sms_all.filtered(lambda sms: sms.state == 'outgoing').send(auto_commit=False, raise_exception=False)

        return True

    def _get_notify_valid_parameters(self):
        return super()._get_notify_valid_parameters() | {'put_in_queue', 'sms_numbers', 'sms_pid_to_number'}

    @api.model
    def notify_cancel_by_type(self, notification_type):
        super().notify_cancel_by_type(notification_type)
        if notification_type == 'sms':
            # TDE CHECK: delete pending SMS
            self._notify_cancel_by_type_generic('sms')
        return True
