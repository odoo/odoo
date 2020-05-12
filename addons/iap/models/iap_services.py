# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import werkzeug.urls

from odoo import api, exceptions, models, _
from odoo.addons.iap.tools import iap_tools

_logger = logging.getLogger(__name__)


class IapServices(models.AbstractModel):
    _name = 'iap.services'
    _description = 'IAP Services Class'

    # ------------------------------------------------------------
    # ENDPOINTS
    # ------------------------------------------------------------

    @api.model
    def _iap_get_endpoint_netloc(self, account_name):
        """ Base netloc for contacting IAP.

        :param account_name: technical name of the account, like 'iap' (for all
        IAP services), 'reveal' (Lead Mining, ...) or 'sms';
        """
        if account_name != 'iap':
            raise ValueError(_('Unrecognized IAP account name: %s' % account_name))
        return iap_tools._iap_get_endpoint(self.env)

    @api.model
    def _iap_get_service_url_scheme(self, service_name):
        """ Scheme when contacting a specific service.

        :param service_name: technical name of the service, like 'iap_balance'
        or 'lead_mining_request';
        """
        if service_name == 'iap_balance':
            return 'iap/1/balance'
        if service_name == 'iap_buy_credit':
            return 'iap/1/credit'
        if service_name == 'my_services':
            return 'iap/services'
        return ValueError(_('Unrecognized IAP service name: %s' % service_name))

    @api.model
    def _iap_get_service_account_match(self, service_name):
        """ From a service, get the related IAP account name. Accounts offer
        several services, making a matching tool required. """
        # make a compatibility account / service name in case of mismatch
        if service_name in ('invoice_ocr', 'partner_autocomplete', 'reveal', 'sms'):
            return service_name
        if service_name in ('iap_balance', 'iap_buy_credit', 'my_services'):
            return 'iap'
        raise ValueError(_('Unrecognized IAP service name: %s' % service_name))

    @api.model
    def _iap_get_service_url(self, service_name):
        """ From a service, get the URL to contact IAP. """
        endpoint_netloc = self._iap_get_endpoint_netloc(self._iap_get_service_account_match(service_name))
        endpoint_scheme = self._iap_get_service_url_scheme(service_name)
        return '%s/%s' % (endpoint_netloc, endpoint_scheme)

    # ------------------------------------------------------------
    # ACCOUNT MANAGEMENT
    # ------------------------------------------------------------

    @api.model
    def _iap_get_service_brand_name(self, service_name):
        return self.env['iap.account']._get_brand_name_from_service_name(service_name)

    @api.model
    def _iap_get_service_account(self, service_name, force_create=True):
        account_name = self._iap_get_service_account_match(service_name)
        return self._iap_get_account(account_name, force_create=force_create)

    @api.model
    def _iap_get_account(self, account_name, force_create=True):
        if not self.env.user.has_group('base.group_user'):
            raise exceptions.AcessError(_('Invalid access to IAP services.'))

        domain = [
            ('service_name', '=', account_name),
            '|', ('company_ids', 'in', self.env.companies.ids), ('company_ids', '=', False)
        ]
        accounts = self.env['iap.account'].sudo().search(domain, order='id desc')
        if not accounts:
            with self.pool.cursor() as cr:
                # Since the account did not exist yet, we will encounter a NoCreditError,
                # which is going to rollback the database and undo the account creation,
                # preventing the process to continue any further.

                # Flush the pending operations to avoid a deadlock.
                self.flush()
                IapAccountSudo = self.env['iap.account'].with_env(self.env(cr=cr)).sudo()
                account = IapAccountSudo.search(domain, order='id desc', limit=1)
                if not account and not force_create:
                    return account
                elif not account:
                    account = IapAccountSudo.create({'service_name': account_name})
                # fetch 'account_token' into cache with this cursor,
                # as self's cursor cannot see this account
                dummy = account.account_token
            return self.env['iap.account'].sudo().browse(account.id)
        accounts_wcompany = accounts.filtered(lambda acc: acc.company_ids)
        if accounts_wcompany:
            return accounts_wcompany[0]
        return accounts[0]

    @api.model
    def iap_get_account_backend_url(self, account_name):
        account = self._iap_get_account(account_name, force_create=True)
        action = self.env.ref('iap.iap_account_action')
        menu = self.env.ref('iap.iap_account_menu')
        if account:
            return "/web#id=%s&action=%s&model=iap.account&view_type=form&menu_id=%s" % (account.id, action.id, menu.id)
        return "/web#action=%s&model=iap.account&view_type=form&menu_id=%s" % (action.id, menu.id)

    # ------------------------------------------------------------
    # BASE / CREDITS SERVICES
    # ------------------------------------------------------------

    @api.model
    def _iap_get_my_services_url(self):
        return '%s?%s' % (
            self._iap_get_service_url('my_services'),
            werkzeug.urls.url_encode({
                'dbuuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
            })
        )

    @api.model
    def _iap_get_service_credits_balance(self, service_name):
        """ Get account balance """
        account = self._iap_get_service_account(service_name, force_create=False)
        if not account:
            return 0
        try:
            credit = iap_tools.iap_jsonrpc(
                url=self._iap_get_service_url('iap_balance'),
                params={
                    'dbuuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
                    'account_token': account.account_token,
                    'service_name': account.service_name,
                }
            )
        # TDE FIXME: try to narrow exception
        except Exception as e:
            _logger.info('Get credit error : %s', str(e))
            credit = -1

        return credit

    @api.model
    def iap_get_service_credits_url(self, service_name, credit=0, trial=False):
        """ Buy credits """
        account = self._iap_get_service_account(service_name, force_create=True)
        url = self._iap_get_service_url('iap_buy_credit')
        return '%s?%s' % (url, werkzeug.urls.url_encode({
            'dbuuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
            'service_name': service_name,
            'account_token': account.account_token,
            'credit': credit,
            'trial': trial,
        }))
