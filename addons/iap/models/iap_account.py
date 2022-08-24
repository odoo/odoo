# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import uuid
import werkzeug.urls

from odoo import api, fields, models
from odoo.addons.iap.tools import iap_tools

_logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = 'https://iap.odoo.com'


class IapAccount(models.Model):
    _name = 'iap.account'
    _rec_name = 'service_name'
    _description = 'IAP Account'

    service_name = fields.Char()
    account_token = fields.Char(default=lambda s: uuid.uuid4().hex)
    company_ids = fields.Many2many('res.company')

    @api.model
    def get(self, service_name, force_create=True):
        domain = [
            ('service_name', '=', service_name),
            '|',
                ('company_ids', 'in', self.env.companies.ids),
                ('company_ids', '=', False)
        ]
        accounts = self.search(domain, order='id desc')
        accounts_without_token = accounts.filtered(lambda acc: not acc.account_token)
        if accounts_without_token:
            with self.pool.cursor() as cr:
                # In case of a further error that will rollback the database, we should
                # use a different SQL cursor to avoid undo the accounts deletion.

                # Flush the pending operations to avoid a deadlock.
                self.flush()
                IapAccount = self.with_env(self.env(cr=cr))
                IapAccount.search(domain + [('account_token', '=', False)]).unlink()
                accounts = accounts - accounts_without_token
        if not accounts:
            with self.pool.cursor() as cr:
                # Since the account did not exist yet, we will encounter a NoCreditError,
                # which is going to rollback the database and undo the account creation,
                # preventing the process to continue any further.

                # Flush the pending operations to avoid a deadlock.
                self.env.flush_all()
                IapAccount = self.with_env(self.env(cr=cr))
                account = IapAccount.search(domain, order='id desc', limit=1)
                if not account:
                    if not force_create:
                        return account
                    account = IapAccount.create({'service_name': service_name})
                # fetch 'account_token' into cache with this cursor,
                # as self's cursor cannot see this account
                account_token = account.account_token
            account = self.browse(account.id)
            self.env.cache.set(account, IapAccount._fields['account_token'], account_token)
            return account
        accounts_with_company = accounts.filtered(lambda acc: acc.company_ids)
        if accounts_with_company:
            return accounts_with_company[0]
        return accounts[0]

    @api.model
    def get_credits_url(self, service_name, base_url='', credit=0, trial=False):
        """ Called notably by ajax crash manager, buy more widget, partner_autocomplete, sanilmail. """
        dbuuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        if not base_url:
            endpoint = iap_tools.iap_get_endpoint(self.env)
            route = '/iap/1/credit'
            base_url = endpoint + route
        account_token = self.get(service_name).account_token
        d = {
            'dbuuid': dbuuid,
            'service_name': service_name,
            'account_token': account_token,
            'credit': credit,
        }
        if trial:
            d.update({'trial': trial})
        return '%s?%s' % (base_url, werkzeug.urls.url_encode(d))

    @api.model
    def get_account_url(self):
        """ Called only by res settings """
        route = '/iap/services'
        endpoint = iap_tools.iap_get_endpoint(self.env)
        d = {'dbuuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid')}

        return '%s?%s' % (endpoint + route, werkzeug.urls.url_encode(d))

    @api.model
    def get_config_account_url(self):
        """ Called notably by ajax partner_autocomplete. """
        account = self.env['iap.account'].get('partner_autocomplete')
        action = self.env.ref('iap.iap_account_action')
        menu = self.env.ref('iap.iap_account_menu')
        no_one = self.user_has_groups('base.group_no_one')
        if account:
            url = "/web#id=%s&action=%s&model=iap.account&view_type=form&menu_id=%s" % (account.id, action.id, menu.id)
        else:
            url = "/web#action=%s&model=iap.account&view_type=form&menu_id=%s" % (action.id, menu.id)
        return no_one and url

    @api.model
    def get_credits(self, service_name):
        account = self.get(service_name, force_create=False)
        credit = 0

        if account:
            route = '/iap/1/balance'
            endpoint = iap_tools.iap_get_endpoint(self.env)
            url = endpoint + route
            params = {
                'dbuuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
                'account_token': account.account_token,
                'service_name': service_name,
            }
            try:
                credit = iap_tools.iap_jsonrpc(url=url, params=params)
            except Exception as e:
                _logger.info('Get credit error : %s', str(e))
                credit = -1

        return credit

    def _neutralize(self):
        super()._neutralize()
        self.env.flush_all()
        self.env.invalidate_all()

        self.env.cr.execute("""
            INSERT INTO ir_config_parameter(key, value)
            VALUES ('iap.endpoint', 'https://iap-sandbox.odoo.com')
            ON CONFLICT (key) DO UPDATE SET value = 'https://iap-sandbox.odoo.com'
        """)

        iap_service_endpoints = self._get_iap_config_parameters()
        if iap_service_endpoints:
            self.env.cr.execute("""
                UPDATE ir_config_parameter
                SET value = 'https://iap-services-test.odoo.com'
                WHERE key IN %s
            """, [tuple(iap_service_endpoints)])

    def _get_iap_config_parameters(self):
        """override this method to extend the list with each parameter"""
        return []
