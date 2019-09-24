# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import threading

from odoo import api, fields, models, tools

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
        'server_error': 'sms_server'
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
    error_code = fields.Selection([
        ('sms_number_missing', 'Missing Number'),
        ('sms_number_format', 'Wrong Number Format'),
        ('sms_credit', 'Insufficient Credit'),
        ('sms_server', 'Server Error'),
        # mass mode specific codes
        ('sms_blacklist', 'Blacklisted'),
        ('sms_duplicate', 'Duplicate'),
    ])

    def send(self, delete_all=False, auto_commit=False, raise_exception=False):
        """ Main API method to send SMS.

          :param delete_all: delete all SMS (sent or not); otherwise delete only
            sent SMS;
          :param auto_commit: commit after each batch of SMS;
          :param raise_exception: raise if there is an issue contacting IAP;
        """
        for batch_ids in self._split_batch():
            self.browse(batch_ids)._send(delete_all=delete_all, raise_exception=raise_exception)
            # auto-commit if asked except in testing mode
            if auto_commit is True and not getattr(threading.currentThread(), 'testing', False):
                self._cr.commit()

    def cancel(self):
        self.state = 'canceled'

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
            auto_commit = not getattr(threading.currentThread(), 'testing', False)
            res = self.browse(ids).send(delete_all=False, auto_commit=auto_commit, raise_exception=False)
        except Exception:
            _logger.exception("Failed processing SMS queue")
        return res

    def _split_batch(self):
        batch_size = int(self.env['ir.config_parameter'].sudo().get_param('sms.session.batch.size', 500))
        for sms_batch in tools.split_every(batch_size, self.ids):
            yield sms_batch

    def _send(self, delete_all=False, raise_exception=False):
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
            self._postprocess_iap_sent_sms([{'res_id': sms.id, 'state': 'server_error'} for sms in self], delete_all=delete_all)
        else:
            _logger.info('Send batch %s SMS: %s: gave %s', len(self.ids), self.ids, iap_results)
            self._postprocess_iap_sent_sms(iap_results, delete_all=delete_all)

    def _postprocess_iap_sent_sms(self, iap_results, failure_reason=None, delete_all=False):
        if delete_all:
            todelete_sms_ids = [item['res_id'] for item in iap_results]
        else:
            todelete_sms_ids = [item['res_id'] for item in iap_results if item['state'] == 'success']

        for state in self.IAP_TO_SMS_STATE.keys():
            sms_ids = [item['res_id'] for item in iap_results if item['state'] == state]
            if sms_ids:
                if state != 'success' and not delete_all:
                    self.env['sms.sms'].sudo().browse(sms_ids).write({
                        'state': 'error',
                        'error_code': self.IAP_TO_SMS_STATE[state],
                    })
                notifications = self.env['mail.notification'].sudo().search([
                    ('notification_type', '=', 'sms'),
                    ('sms_id', 'in', sms_ids),
                    ('notification_status', 'not in', ('sent', 'canceled'))]
                )
                if notifications:
                    notifications.write({
                        'notification_status': 'sent' if state == 'success' else 'exception',
                        'failure_type': self.IAP_TO_SMS_STATE[state] if state != 'success' else False,
                        'failure_reason': failure_reason if failure_reason else False,
                    })

        if todelete_sms_ids:
            self.browse(todelete_sms_ids).sudo().unlink()
