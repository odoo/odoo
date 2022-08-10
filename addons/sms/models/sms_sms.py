# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import threading
from uuid import uuid4
from itertools import groupby
from collections import defaultdict

from odoo import api, fields, models, tools, _

_logger = logging.getLogger(__name__)


class SmsSms(models.Model):
    _name = 'sms.sms'
    _description = 'Outgoing SMS'
    _rec_name = 'number'
    _order = 'id DESC'

    IAP_TO_SMS_STATE = {
        'success': 'sent',
        'insufficient_credit': 'sms_credit',
        'wrong_number_format': 'sms_number_format',
        'server_error': 'sms_server',
        'unregistered': 'sms_acc',
        # delivery report errors (DLR)
        'not_allowed': 'sms_not_allowed',
        'invalid_destination': 'sms_invalid_destination',
        'rejected': 'sms_rejected',
        'expired': 'sms_expired',
    }

    number = fields.Char('Number')
    body = fields.Text()
    partner_id = fields.Many2one('res.partner', 'Customer')
    mail_message_id = fields.Many2one('mail.message', index=True)
    state = fields.Selection([
        ('outgoing', 'In Queue'),
        ('processing', 'Processing'),
        ('sent', 'Sent'),
        ('error', 'Error'),
        ('canceled', 'Canceled')
    ], 'SMS Status', readonly=True, copy=False, default='outgoing', required=True)
    failure_type = fields.Selection([
        ('sms_number_missing', 'Missing Number'),
        ('sms_number_format', 'Wrong Number Format'),
        ('sms_credit', 'Insufficient Credit'),
        ('sms_server', 'Server Error'),
        ('sms_acc', 'Unregistered Account'),
        # mass mode specific codes
        ('sms_blacklist', 'Blacklisted'),
        ('sms_duplicate', 'Duplicate'),
        ('sms_optout', 'Opted Out'),
        # delivery report errors (DLR)
        ('sms_not_allowed', 'Not Allowed'),
        ('sms_invalid_destination', 'Invalid Destination'),
        ('sms_rejected', 'Rejected'),
        ('sms_expired', 'Expired'),
    ], copy=False)
    uuid = fields.Char(
        'UUID', help="UUID used by sms service",
        required=True, copy=False, readonly=True, index=True, default=lambda r: uuid4().hex)

    _sql_constraints = [
        ('uuid_unique', 'unique(uuid)', 'UUID should be unique'),
    ]

    def action_set_canceled(self):
        self.state = 'canceled'
        notifications = self.env['mail.notification'].sudo().search([
            ('sms_id', 'in', self.ids),
            # sent is sent -> cannot reset
            ('notification_status', 'not in', ['canceled', 'sent']),
        ])
        if notifications:
            notifications.write({'notification_status': 'canceled'})
            if not self._context.get('sms_skip_msg_notification', False):
                notifications.mail_message_id._notify_message_notification_update()

    def action_set_error(self, failure_type):
        self.state = 'error'
        self.failure_type = failure_type
        notifications = self.env['mail.notification'].sudo().search([
            ('sms_id', 'in', self.ids),
            # sent can be set to error due to IAP feedback
            ('notification_status', '!=', 'exception'),
        ])
        if notifications:
            notifications.write({'notification_status': 'exception', 'failure_type': failure_type})
            if not self._context.get('sms_skip_msg_notification', False):
                notifications.mail_message_id._notify_message_notification_update()

    def action_set_outgoing(self):
        self.write({
            'state': 'outgoing',
            'failure_type': False
        })
        notifications = self.env['mail.notification'].sudo().search([
            ('sms_id', 'in', self.ids),
            # sent is sent -> cannot reset
            ('notification_status', 'not in', ['ready', 'sent']),
        ])
        if notifications:
            notifications.write({'notification_status': 'ready', 'failure_type': False})
            if not self._context.get('sms_skip_msg_notification', False):
                notifications.mail_message_id._notify_message_notification_update()

    def update_status(self, sms_status):
        self.state = 'sent'
        if sms_status in {'delivered', 'sent', 'not_delivered'}:
            self.unlink()
        else:
            self.action_set_error(self.IAP_TO_SMS_STATE.get(sms_status))

    def send(self, unlink_failed=False, auto_commit=False, raise_exception=False):
        """ Main API method to send SMS.

          :param unlink_failed: unlink failed SMS after IAP feedback;
          :param auto_commit: commit after each batch of SMS;
          :param raise_exception: raise if there is an issue contacting IAP;
        """
        for batch_ids in self._split_batch():
            self.browse(batch_ids)._send(unlink_failed=unlink_failed, raise_exception=raise_exception)
            # auto-commit if asked except in testing mode
            if auto_commit is True and not getattr(threading.current_thread(), 'testing', False):
                self._cr.commit()

    def resend_failed(self):
        sms_to_send = self.filtered(lambda sms: sms.state == 'error')
        notification_title = _('Warning')
        notification_type = 'danger'
        notification_message = ''
        if sms_to_send:
            sms_to_send.send()
            success_sms = len(sms_to_send) - len(sms_to_send.exists())
            if success_sms > 0:
                notification_title = _('Success')
                notification_type = 'success'
                notification_message = _('%s out of the %s selected SMS Text Messages have successfully been resent.', success_sms, len(self))
            else:
                notification_message = _('The SMS Text Messages could not be resent.')
        else:
            notification_message = _('There are no SMS Text Messages to resend.')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': notification_title,
                'message': notification_message,
                'type': notification_type,
            }
        }

    @api.model
    def _process_queue(self, ids=None):
        """ Send immediately queued messages, committing after each message is sent.
        This is not transactional and should not be called during another transaction!

       :param list ids: optional list of emails ids to send. If passed no search
         is performed, and these ids are used instead.
        """
        domain = [('state', '=', 'outgoing')]

        filtered_ids = self.search(domain, limit=10000).ids  # TDE note: arbitrary limit we might have to update
        if ids:
            ids = list(set(filtered_ids) & set(ids))
        else:
            ids = filtered_ids
        ids.sort()

        res = None
        try:
            # auto-commit except in testing mode
            auto_commit = not getattr(threading.current_thread(), 'testing', False)
            res = self.browse(ids).send(unlink_failed=False, auto_commit=auto_commit, raise_exception=False)
        except Exception:
            _logger.exception("Failed processing SMS queue")
        return res

    def _split_batch(self):
        batch_size = int(self.env['ir.config_parameter'].sudo().get_param('sms.session.batch.size', 500))
        for sms_batch in tools.split_every(batch_size, self.ids):
            yield sms_batch

    def _send(self, unlink_failed=False, raise_exception=False):
        """ This method tries to send SMS after checking the number (presence and
        formatting). """
        messages = defaultdict(list)
        for record in self:
            messages[record.body].append({
                'number': record.number,
                'uuid': record.uuid,
            })
        try:
            iap_results = self.env['sms.api']._send_sms_batch([{
                'content': content,
                'numbers': numbers,
            } for content, numbers in messages.items()], dlr=True)
        except Exception as e:
            _logger.info('Sent batch %s SMS: %s: failed with exception %s', len(self.ids), self.ids, e)
            if raise_exception:
                raise
            self._postprocess_iap_sent_sms(
                [{'uuid': sms.uuid, 'state': 'server_error'} for sms in self],
                unlink_failed=unlink_failed)
        else:
            _logger.info('Send batch %s SMS: %s: gave %s', len(self.ids), self.ids, iap_results)
            self._postprocess_iap_sent_sms(iap_results, unlink_failed=unlink_failed)

    def _postprocess_iap_sent_sms(self, iap_results, failure_reason=None, unlink_failed=False):
        todelete_sms_uuids = []
        if unlink_failed:
            todelete_sms_uuids += [item['uuid'] for item in iap_results if item['state'] != 'success']

        key = lambda result: result['state']
        for state, results in groupby(sorted(iap_results, key=key), key=key):
            uuids = tuple(result['uuid'] for result in results)
            sms = self.env['sms.sms'].sudo().search(
                [('uuid', 'in', uuids)])
            if state != 'success' and not unlink_failed:
                sms.write({
                    'state': 'error',
                    'failure_type': self.IAP_TO_SMS_STATE[state],
                })
            if state == 'success':
                sms.write({
                    'state': 'processing',
                    'failure_type': False,
                })
            notifications = self.env['mail.notification'].sudo().search([
                ('notification_type', '=', 'sms'),
                ('sms_id', 'in', sms.ids),
                ('notification_status', 'not in', ('sent', 'canceled')),
            ])
            if notifications:
                notifications.write({
                    'notification_status': 'sent' if state == 'success' else 'exception',
                    'failure_type': self.IAP_TO_SMS_STATE[state] if state != 'success' else False,
                    'failure_reason': failure_reason if failure_reason else False,
                })
        self.mail_message_id._notify_message_notification_update()

        if todelete_sms_uuids:
            self.env['sms.sms'].sudo().search([('uuid', 'in', todelete_sms_uuids)]).unlink()
