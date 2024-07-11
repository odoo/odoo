# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re

from odoo.exceptions import UserError
from odoo.http import Controller, request, route

_logger = logging.getLogger(__name__)


class SmsController(Controller):

    @route('/sms/status', type='json', auth='public')
    def update_sms_status(self, message_statuses):
        """Receive a batch of delivery reports from IAP

        :param message_statuses:
            [
                {
                    'sms_status': status0,
                    'uuids': [uuid00, uuid01, ...],
                }, {
                    'sms_status': status1,
                    'uuids': [uuid10, uuid11, ...],
                },
                ...
            ]
        """
        all_uuids = []
        for uuids, iap_status in ((status['uuids'], status['sms_status']) for status in message_statuses):
            self._check_status_values(uuids, iap_status, message_statuses)
            if sms_trackers_sudo := request.env['sms.tracker'].sudo().search([('sms_uuid', 'in', uuids)]):
                if state := request.env['sms.sms'].IAP_TO_SMS_STATE_SUCCESS.get(iap_status):
                    sms_trackers_sudo._action_update_from_sms_state(state)
                else:
                    sms_trackers_sudo._action_update_from_provider_error(iap_status)
            all_uuids += uuids
        request.env['sms.sms'].sudo().search([('uuid', 'in', all_uuids), ('to_delete', '=', False)]).to_delete = True
        return 'OK'

    @staticmethod
    def _check_status_values(uuids, iap_status, message_statuses):
        """Basic checks to avoid unnecessary queries and allow debugging."""
        if (not uuids or not iap_status or not re.match(r'^\w+$', iap_status)
                or any(not re.match(r'^[0-9a-f]{32}$', uuid) for uuid in uuids)):
            _logger.warning('Received ill-formatted SMS delivery report event: \n%s', message_statuses)
            raise UserError("Bad parameters")
