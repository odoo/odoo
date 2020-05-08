# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, exceptions, models, _
from odoo.addons.iap.tools import iap_tools


class IapServices(models.AbstractModel):
    _inherit = 'iap.services'

    # ------------------------------------------------------------
    # ENDPOINTS
    # ------------------------------------------------------------

    @api.model
    def _iap_get_endpoint_netloc(self, account_name):
        if account_name == 'sms':
            return self.env['ir.config_parameter'].sudo().get_param('sms.endpoint', 'https://iap-sms.odoo.com')
        if account_name == 'snailmail':
            return self.env['ir.config_parameter'].sudo().get_param('snailmail.endpoint', 'https://iap-snailmail.odoo.com')
        return super(IapServices, self)._iap_get_endpoint_netloc(account_name)

    @api.model
    def _iap_get_service_account_match(self, service_name):
        if service_name in ('sms', 'sms_send', 'sms_single'):
            return 'sms'
        if service_name in ('snailmail', 'snailmail_print'):
            return 'snailmail'
        return super(IapServices, self)._iap_get_service_account_match(service_name)

    @api.model
    def _iap_get_service_url_scheme(self, service_name):
        if service_name == 'sms_send':
            return 'iap/sms/1/send'
        if service_name == 'sms_single':
            return 'iap/message_send'
        if service_name == 'snailmail_print':
            return 'iap/snailmail/1/print'
        return super(IapServices, self)._iap_get_service_url_scheme(service_name)

    # ------------------------------------------------------------
    # REQUESTS
    # ------------------------------------------------------------

    @api.model
    def _iap_request_snailmail_print(self, documents, options, batch=True):
        """ Send a snailmail print request

        :return response: {
            'request_code': RESPONSE_OK, # because we receive 200 if good or fail
            'total_cost': total_cost,
            'credit_error': credit_error,
            'request': {
                'documents': documents,
                'options': options
                }
            }
        }
        """
        snailmail_account = self.env['iap.services']._iap_get_service_account('snailmail_print')
        params = {
            'account_token': snailmail_account.account_token,
            'dbuuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
            'documents': documents,
            'options': options,
            'batch': batch,
        }
        return iap_tools.iap_jsonrpc(self._iap_get_service_url('snailmail_print'), params=params)

    @api.model
    def _iap_request_sms_single(self, numbers, message):
        """ Send a single message to several numbers

        :param numbers: list of E164 formatted phone numbers
        :param message: content to send

        :raises ? TDE FIXME
        """
        sms_account = self.env['iap.services']._iap_get_service_account('sms_single')
        params = {
            'account_token': sms_account.account_token,
            'numbers': numbers,
            'message': message,
        }
        return iap_tools.iap_jsonrpc(self._iap_get_service_url('sms_single'), params=params)

    @api.model
    def _iap_request_sms_send(self, messages):
        """ Send SMS using IAP in batch mode

        :param messages: list of SMS to send, structured as dict [{
            'res_id':  integer: ID of sms.sms,
            'number':  string: E164 formatted phone number,
            'content': string: content to send
        }]

        :return: return of /iap/sms/1/send controller which is a list of dict [{
            'res_id': integer: ID of sms.sms,
            'state':  string: 'insufficient_credit' or 'wrong_number_format' or 'success',
            'credit': integer: number of credits spent to send this SMS,
        }]

        :raises: normally none
        """
        sms_account = self.env['iap.services']._iap_get_service_account('sms_send')
        params = {
            'account_token': sms_account.account_token,
            'messages': messages
        }
        return iap_tools.iap_jsonrpc(self._iap_get_service_url('sms_send'), params=params)

    # ------------------------------------------------------------
    # MAIL HELPERS AND TOOLS
    # ------------------------------------------------------------

    @api.model
    def _iap_notify_nocredit(self, service_name, model_name, notification_parameter=None):
        """ Notify about missing creadits. An optional notification parameter can be used
        to avoid spamming people. """
        iap_account = self._iap_get_service_account(service_name, force_create=False)
        if not iap_account:
            return False

        if notification_parameter:
            already_notified = self.env['ir.config_parameter'].sudo().get_param(notification_parameter, False)
            if already_notified:
                return False

        mail_template = self.env.ref('iap_mail.mail_template_iap_service_no_credits', raise_if_not_found=False)
        if not mail_template:
            return False

        # Get the email address of the creators of the records
        res = self.env[model_name].search_read([], ['create_uid'], limit=100)
        uids = set(r['create_uid'][0] for r in res if r.get('create_uid'))
        res = self.env['res.users'].search_read([('id', 'in', list(uids))], ['email'])
        emails = set(r['email'] for r in res if r.get('email'))

        email_values = {
            'email_to': ','.join(emails)
        }
        mail_template.send_mail(iap_account.id, force_send=True, email_values=email_values)

        if notification_parameter:
            self.env['ir.config_parameter'].sudo().set_param(notification_parameter, True)
        return True
