# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import uuid

from requests.exceptions import HTTPError

from odoo import api, exceptions, models, release, _
from odoo.addons.iap.tools import iap_tools

_logger = logging.getLogger(__name__)


class IapServices(models.AbstractModel):
    _inherit = 'iap.services'

    # ------------------------------------------------------------
    # ENDPOINTS
    # ------------------------------------------------------------

    @api.model
    def _iap_get_endpoint_netloc(self, account_name):
        if account_name == 'ocn':
            return self.env['ir.config_parameter'].sudo().get_param('odoo_ocn.endpoint', 'https://ocn.odoo.com')
        if account_name == 'partner_autocomplete':
            return self.env['ir.config_parameter'].sudo().get_param('iap.partner_autocomplete.endpoint', 'https://partner-autocomplete.odoo.com')
        if account_name == 'sms':
            return self.env['ir.config_parameter'].sudo().get_param('sms.endpoint', 'https://iap-sms.odoo.com')
        if account_name == 'snailmail':
            return self.env['ir.config_parameter'].sudo().get_param('snailmail.endpoint', 'https://iap-snailmail.odoo.com')
        return super(IapServices, self)._iap_get_endpoint_netloc(account_name)

    @api.model
    def _iap_get_service_account_match(self, service_name):
        if service_name in ('ocn', 'ocn_enable_service', 'ocn_register_device'):
            return 'ocn'
        if service_name in ('partner_autocomplete',
                            'partner_autocomplete_enrich',
                            'partner_autocomplete_search',
                            'partner_autocomplete_search_vat'):
            return 'partner_autocomplete'
        if service_name in ('sms', 'sms_send', 'sms_single'):
            return 'sms'
        if service_name in ('snailmail', 'snailmail_print'):
            return 'snailmail'
        return super(IapServices, self)._iap_get_service_account_match(service_name)

    @api.model
    def _iap_get_service_url_scheme(self, service_name):
        if service_name == 'ocn_enable_service':
            return 'iap/ocn/enable_service'
        if service_name == 'ocn_register_device':
            return 'iap/ocn/register_device'
        if service_name == 'partner_autocomplete_enrich':
            return 'iap/partner_autocomplete/enrich'
        if service_name == 'partner_autocomplete_search':
            return 'iap/partner_autocomplete/search'
        if service_name == 'partner_autocomplete_search_vat':
            return 'iap/partner_autocomplete/search_vat'
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
    def _iap_ocn_get_uuid(self):
        push_uuid = self.env['ir.config_parameter'].sudo().get_param('ocn.uuid')
        if not push_uuid:
            push_uuid = str(uuid.uuid4())
            self.env['ir.config_parameter'].sudo().set_param('ocn.uuid', push_uuid)
        return push_uuid

    @api.model
    def _iap_request_ocn_enable_service(self):
        params = {
            'ocnuuid': self._iap_ocn_get_uuid(),
            'server_version': release.version,
            'db': self.env.cr.dbname,
            'company_name': self.env.company.name,
            'url': self.env['ir.config_parameter'].sudo().get_param('web.base.url'),
        }
        return iap_tools.iap_jsonrpc(self._iap_get_service_url('ocn_enable_service'), params=params)

    @api.model
    def _iap_request_ocn_register_device(self, device_name, device_key):
        params = {
            'ocn_uuid': self._iap_ocn_get_uuid(),
            'user_name': self.env.user.partner_id.name,
            'user_login': self.env.user.login,
            'device_name': device_name,
            'device_key': device_key,
        }
        return iap_tools.iap_jsonrpc(self._iap_get_service_url('ocn_register_device'), params=params)

    def _iap_partner_autocomplete_params(self):
        return {
            'account_token': self.env['iap.services']._iap_get_service_account('partner_autocomplete', force_create=False).account_token,
            'dbuuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
            'country_code': self.env.company.country_id.code,
            'zip': self.env.company.z
        }

    @api.model
    def _iap_request_partner_autocomplete_enrich(self, domain, partner_gid, vat):
        """

        :return result: tuple(results, error)
        """
        params = dict(self._iap_partner_autocomplete_params(), domain=domain, partner_gid=partner_gid, vat=vat)
        return iap_tools.iap_jsonrpc(self._iap_get_service_url('partner_autocomplete_enrich'), params=params, timeout=15)

    @api.model
    def _iap_request_partner_autocomplete_search(self, query):
        params = dict(self._iap_partner_autocomplete_params(), query=query)
        return iap_tools.iap_jsonrpc(self._iap_get_service_url('partner_autocomplete_search'), params=params, timeout=15)

    @api.model
    def _iap_request_partner_autocomplete_search_vat(self, vat):
        params = dict(self._iap_partner_autocomplete_params(), vat=vat)
        return iap_tools.iap_jsonrpc(self._iap_get_service_url('partner_autocomplete_search_vat'), params=params, timeout=15)

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
    # PARTNER HELPERS AND TOOLS
    # ------------------------------------------------------------

    @api.model
    def _iap_get_partner_autocomplete(self, service_name, **params):
        """ UPDATE ME, DON'T KNOW WHAT PA IS TRYING TO DO """
        pa_account = self.env['iap.services']._iap_get_account('partner_autocomplete', force_create=False)
        if not pa_account.account_token:
            return False, 'No Account Token'
        try:
            if service_name == 'partner_autocomplete_enrich':
                results = self._iap_request_partner_autocomplete_enrich(**params)
            elif service_name == 'partner_autocomplete_search':
                results = self._iap_request_partner_autocomplete_search(**params)
            elif service_name == 'partner_autocomplete_search_vat':
                results = self._iap_request_partner_autocomplete_search_vat(**params)
            else:
                raise ValueError(_('Invalid partner autocompletion service'))

        except (ConnectionError, HTTPError, exceptions.AccessError, exceptions.UserError) as exception:
            _logger.error('Autocomplete API error: %s' % str(exception))
            return False, str(exception)

        except iap_tools.InsufficientCreditError as exception:
            _logger.warning('Insufficient Credits for Autocomplete Service: %s' % str(exception))
            return False, 'Insufficient Credit'

        return results, False

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
