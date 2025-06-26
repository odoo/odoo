# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from uuid import uuid4

from werkzeug.urls import url_join

from odoo import api, fields, models, tools, _
from odoo.addons.sms.tools.sms_api import SmsApi

_logger = logging.getLogger(__name__)


class SmsSms(models.Model):
    _name = 'sms.sms'
    _description = 'Outgoing SMS'
    _rec_name = 'number'
    _order = 'id DESC'

    IAP_TO_SMS_STATE_SUCCESS = {
        'processing': 'process',
        'success': 'pending',
        # These below are not returned in responses from IAP API in _send but are received via webhook events.
        'sent': 'pending',
        'delivered': 'sent',
    }
    IAP_TO_SMS_FAILURE_TYPE = {
        'insufficient_credit': 'sms_credit',
        'wrong_number_format': 'sms_number_format',
        'country_not_supported': 'sms_country_not_supported',
        'server_error': 'sms_server',
        'unregistered': 'sms_acc'
    }

    BOUNCE_DELIVERY_ERRORS = {'sms_invalid_destination', 'sms_not_allowed', 'sms_rejected'}
    DELIVERY_ERRORS = {'sms_expired', 'sms_not_delivered', *BOUNCE_DELIVERY_ERRORS}

    uuid = fields.Char('UUID', copy=False, readonly=True, default=lambda self: uuid4().hex,
                       help='Alternate way to identify a SMS record, used for delivery reports')
    number = fields.Char('Number')
    body = fields.Text()
    partner_id = fields.Many2one('res.partner', 'Customer')
    mail_message_id = fields.Many2one('mail.message', index=True)
    state = fields.Selection([
        ('outgoing', 'In Queue'),
        ('process', 'Processing'),
        ('pending', 'Sent'),
        ('sent', 'Delivered'),  # As for notifications and traces
        ('error', 'Error'),
        ('canceled', 'Cancelled')
    ], 'SMS Status', readonly=True, copy=False, default='outgoing', required=True)
    failure_type = fields.Selection([
        ("unknown", "Unknown error"),
        ('sms_number_missing', 'Missing Number'),
        ('sms_number_format', 'Wrong Number Format'),
        ('sms_country_not_supported', 'Country Not Supported'),
        ('sms_registration_needed', 'Country-specific Registration Required'),
        ('sms_credit', 'Insufficient Credit'),
        ('sms_server', 'Server Error'),
        ('sms_acc', 'Unregistered Account'),
        # mass mode specific codes, generated internally, not returned by IAP.
        ('sms_blacklist', 'Blacklisted'),
        ('sms_duplicate', 'Duplicate'),
        ('sms_optout', 'Opted Out'),
    ], copy=False)
    sms_tracker_id = fields.Many2one('sms.tracker', string='SMS trackers', compute='_compute_sms_tracker_id')
    to_delete = fields.Boolean(
        'Marked for deletion', default=False,
        help='Will automatically be deleted, while notifications will not be deleted in any case.'
    )

    _uuid_unique = models.Constraint(
        'unique(uuid)',
        'UUID must be unique',
    )

    @api.model_create_multi
    def create(self, vals_list):
        self.env.ref('sms.ir_cron_sms_scheduler_action')._trigger()
        return super().create(vals_list)

    @api.depends('uuid')
    def _compute_sms_tracker_id(self):
        self.sms_tracker_id = False
        existing_trackers = self.env['sms.tracker'].search([('sms_uuid', 'in', self.filtered('uuid').mapped('uuid'))])
        tracker_ids_by_sms_uuid = {tracker.sms_uuid: tracker.id for tracker in existing_trackers}
        for sms in self.filtered(lambda s: s.uuid in tracker_ids_by_sms_uuid):
            sms.sms_tracker_id = tracker_ids_by_sms_uuid[sms.uuid]

    def action_set_canceled(self):
        self._update_sms_state_and_trackers('canceled')

    def action_set_error(self, failure_type):
        self._update_sms_state_and_trackers('error', failure_type=failure_type)

    def action_set_outgoing(self):
        self._update_sms_state_and_trackers('outgoing', failure_type=False)

    def send(self, unlink_failed=False, unlink_sent=True, raise_exception=False):
        """ Main API method to send SMS.

        This contacts an external server. If the transaction fails, it may be
        retried which can result in sending multiple SMS messages!

          :param unlink_failed: unlink failed SMS after IAP feedback;
          :param unlink_sent: unlink sent SMS after IAP feedback;
          :param raise_exception: raise if there is an issue contacting IAP;
        """

        domain = [('state', '=', 'outgoing'), ('to_delete', '!=', True)]
        records = self.try_lock_for_update().filtered_domain(domain)
        for batch_ids in tools.split_every(self._get_send_batch_size(), records.ids):
            records = self.browse(batch_ids)
            records._send(unlink_failed=unlink_failed, unlink_sent=unlink_sent, raise_exception=raise_exception)

    def resend_failed(self):
        sms_to_send = self.filtered(lambda sms: sms.state == 'error' and not sms.to_delete)
        sms_to_send.state = 'outgoing'
        notification_title = _('Warning')
        notification_type = 'danger'

        if sms_to_send:
            sms_to_send.send()
            success_sms = len(sms_to_send) - len(sms_to_send.exists())
            if success_sms > 0:
                notification_title = _('Success')
                notification_type = 'success'
                notification_message = _('%(count)s out of the %(total)s selected SMS Text Messages have successfully been resent.', count=success_sms, total=len(self))
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
    def _process_queue(self):
        """ CRON job to send queued SMS messages. """
        domain = [('state', '=', 'outgoing'), ('to_delete', '!=', True)]

        batch_size = self._get_send_batch_size()
        records = self.search(domain, limit=batch_size, order='id').try_lock_for_update()
        if not records:
            return

        records._send(unlink_failed=False, unlink_sent=True, raise_exception=False)
        self.env['ir.cron']._commit_progress(len(records), remaining=self.search_count(domain) if len(records) == batch_size else 0)

    def _get_send_batch_size(self):
        return int(self.env['ir.config_parameter'].sudo().get_param('sms.session.batch.size', 500))

    def _send(self, unlink_failed=False, unlink_sent=True, raise_exception=False):
        """Send SMS after checking the number (presence and formatting)."""
        messages = [{
            'content': body,
            'numbers': [{'number': sms.number, 'uuid': sms.uuid} for sms in body_sms_records],
        } for body, body_sms_records in self.grouped('body').items()]

        delivery_reports_url = url_join(self[0].get_base_url(), '/sms/status')
        try:
            results = SmsApi(self.env)._send_sms_batch(messages, delivery_reports_url=delivery_reports_url)
        except Exception as e:
            _logger.info('Sent batch %s SMS: %s: failed with exception %s', len(self.ids), self.ids, e)
            if raise_exception:
                raise
            results = [{'uuid': sms.uuid, 'state': 'server_error'} for sms in self]
        else:
            _logger.info('Send batch %s SMS: %s: gave %s', len(self.ids), self.ids, results)

        results_uuids = [result['uuid'] for result in results]
        all_sms_sudo = self.env['sms.sms'].sudo().search([('uuid', 'in', results_uuids)]).with_context(sms_skip_msg_notification=True)

        for iap_state, results_group in tools.groupby(results, key=lambda result: result['state']):
            sms_sudo = all_sms_sudo.filtered(lambda s: s.uuid in {result['uuid'] for result in results_group})
            if success_state := self.IAP_TO_SMS_STATE_SUCCESS.get(iap_state):
                sms_sudo.sms_tracker_id._action_update_from_sms_state(success_state)
                to_delete = {'to_delete': True} if unlink_sent else {}
                sms_sudo.write({'state': success_state, 'failure_type': False, **to_delete})
            else:
                failure_type = self.IAP_TO_SMS_FAILURE_TYPE.get(iap_state, 'unknown')
                if failure_type != 'unknown':
                    sms_sudo.sms_tracker_id._action_update_from_sms_state('error', failure_type=failure_type)
                else:
                    sms_sudo.sms_tracker_id._action_update_from_provider_error(iap_state)
                to_delete = {'to_delete': True} if unlink_failed else {}
                sms_sudo.write({'state': 'error', 'failure_type': failure_type, **to_delete})

        all_sms_sudo.mail_message_id._notify_message_notification_update()

    def _update_sms_state_and_trackers(self, new_state, failure_type=None):
        """Update sms state update and related tracking records (notifications, traces)."""
        self.write({'state': new_state, 'failure_type': failure_type})
        self.sms_tracker_id._action_update_from_sms_state(new_state, failure_type=failure_type)

    @api.autovacuum
    def _gc_device(self):
        self.env.cr.execute("DELETE FROM sms_sms WHERE to_delete = TRUE")
        _logger.info("GC'd %d sms marked for deletion", self.env.cr.rowcount)
