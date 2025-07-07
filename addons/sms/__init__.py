# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
    'unregistered': 'sms_acc',
}

BOUNCE_DELIVERY_ERRORS = {'sms_invalid_destination', 'sms_not_allowed', 'sms_rejected'}

DELIVERY_ERRORS = {'sms_expired', 'sms_not_delivered', *BOUNCE_DELIVERY_ERRORS}

SMS_STATE_TO_NOTIFICATION_STATUS = {
    'canceled': 'canceled',
    'process': 'process',
    'error': 'exception',
    'outgoing': 'ready',
    'sent': 'sent',
    'pending': 'pending',
}

from . import controllers
from . import models
from . import tools
from . import wizard
