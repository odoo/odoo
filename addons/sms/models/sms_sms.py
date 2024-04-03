# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import threading

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
        'unregistered': 'sms_acc'
    }

    number = fields.Char('Number')
    body = fields.Text()
    partner_id = fields.Many2one('res.partner', 'Customer')
    mail_message_id = fields.Many2one('mail.message', index=True)
    state = fields.Selection([
        ('outgoing', 'In Queue'),
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
    ], copy=False)

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

    def send(self, unlink_failed=False, unlink_sent=True, auto_commit=False, raise_exception=False):
        """ Main API method to send SMS.

          :param unlink_failed: unlink failed SMS after IAP feedback;
          :param unlink_sent: unlink sent SMS after IAP feedback;
          :param auto_commit: commit after each batch of SMS;
          :param raise_exception: raise if there is an issue contacting IAP;
        """
        self = self.filtered(lambda sms: sms.state == 'outgoing')
        for batch_ids in self._split_batch():
            self.browse(batch_ids)._send(unlink_failed=unlink_failed, unlink_sent=unlink_sent, raise_exception=raise_exception)
            # auto-commit if asked except in testing mode
            if auto_commit is True and not getattr(threading.current_thread(), 'testing', False):
                self._cr.commit()

    def resend_failed(self):
        sms_to_send = self.filtered(lambda sms: sms.state == 'error')
        sms_to_send.state = 'outgoing'
        notification_title = _('Warning')
        notification_type = 'danger'

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
            res = self.browse(ids).send(unlink_failed=False, unlink_sent=True, auto_commit=auto_commit, raise_exception=False)
        except Exception:
            _logger.exception("Failed processing SMS queue")
        return res

    def _split_batch(self):
        batch_size = int(self.env['ir.config_parameter'].sudo().get_param('sms.session.batch.size', 500))
        for sms_batch in tools.split_every(batch_size, self.ids):
            yield sms_batch

    def _send(self, unlink_failed=False, unlink_sent=True, raise_exception=False):
        """ This method tries to send SMS after checking the number (presence and
        formatting). """
        iap_data = [{
            'res_id': record.id,
            'number': record.number,
            'content': record.body,
        } for record in self]

        try:
            iap_results = self.env['sms.api']._send_sms_batch(iap_data)
        except Exception as e:
            _logger.info('Sent batch %s SMS: %s: failed with exception %s', len(self.ids), self.ids, e)
            if raise_exception:
                raise
            self._postprocess_iap_sent_sms(
                [{'res_id': sms.id, 'state': 'server_error'} for sms in self],
                unlink_failed=unlink_failed, unlink_sent=unlink_sent)
        else:
            _logger.info('Send batch %s SMS: %s: gave %s', len(self.ids), self.ids, iap_results)
            self._postprocess_iap_sent_sms(iap_results, unlink_failed=unlink_failed, unlink_sent=unlink_sent)

    def _postprocess_iap_sent_sms(self, iap_results, failure_reason=None, unlink_failed=False, unlink_sent=True):
        todelete_sms_ids = []
        if unlink_failed:
            todelete_sms_ids += [item['res_id'] for item in iap_results if item['state'] != 'success']
        if unlink_sent:
            todelete_sms_ids += [item['res_id'] for item in iap_results if item['state'] == 'success']

        for state in self.IAP_TO_SMS_STATE.keys():
            sms_ids = [item['res_id'] for item in iap_results if item['state'] == state]
            if sms_ids:
                if state != 'success' and not unlink_failed:
                    self.env['sms.sms'].sudo().browse(sms_ids).write({
                        'state': 'error',
                        'failure_type': self.IAP_TO_SMS_STATE[state],
                    })
                if state == 'success' and not unlink_sent:
                    self.env['sms.sms'].sudo().browse(sms_ids).write({
                        'state': 'sent',
                        'failure_type': False,
                    })
                notifications = self.env['mail.notification'].sudo().search([
                    ('notification_type', '=', 'sms'),
                    ('sms_id', 'in', sms_ids),
                    ('notification_status', 'not in', ('sent', 'canceled')),
                ])
                if notifications:
                    notifications.write({
                        'notification_status': 'sent' if state == 'success' else 'exception',
                        'failure_type': self.IAP_TO_SMS_STATE[state] if state != 'success' else False,
                        'failure_reason': failure_reason if failure_reason else False,
                    })
        self.mail_message_id._notify_message_notification_update()

        if todelete_sms_ids:
            self.browse(todelete_sms_ids).sudo().unlink()
