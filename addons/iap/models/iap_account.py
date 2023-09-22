# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import threading
import uuid
import werkzeug.urls

from odoo import api, fields, models
from odoo.addons.iap.tools import iap_tools
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = 'https://iap.odoo.com'


class IapAccount(models.Model):
    _name = 'iap.account'
    _rec_name = 'service_name'
    _description = 'IAP Account'

    name = fields.Char()
    service_name = fields.Char(readonly=True)
    account_token = fields.Char(
        default=lambda s: uuid.uuid4().hex,
        help="Account token is your authentication key for this service. Do not share it.",
        size=43)
    company_ids = fields.Many2many('res.company')
    account_info_id = fields.Many2one(
        'iap.account.info', compute='_compute_info', inverse='_inverse_info', search='_search_info')
    account_info_ids = fields.One2many(
        'iap.account.info', 'account_id',
        string="Accounts from IAP")
    balance = fields.Char(compute='_compute_balance')
    description = fields.Char(related='account_info_id.description')
    warn_me = fields.Boolean(
        related='account_info_id.warn_me',
        help="We will send you an email when your balance gets below that threshold",
        readonly=False)
    warning_threshold = fields.Float(related='account_info_id.warning_threshold', readonly=False)
    warning_email = fields.Char(related='account_info_id.warning_email', readonly=False)
    show_token = fields.Boolean()

    @api.model
    def get_view(self, view_id=None, view_type='form', **kwargs):
        res = super().get_view(view_id, view_type, **kwargs)
        if view_type == 'tree':
            self.env['iap.account'].get_services()
        return res

    @api.depends('account_info_ids')
    def _compute_info(self):
        for account in self:
            if account.account_info_ids:
                account.account_info_id = account.account_info_ids[-1]

    @api.depends('account_info_id')
    def _compute_balance(self):
        for account in self:
            account.balance = f'{account.account_info_id.balance} {account.account_info_id.unit_name}' if account.account_info_id else "0 Credits"

    def _inverse_info(self):
        for account in self:
            if account.account_info_ids:
                # delete previous reference
                account_info = account.env['iap.account.info'].browse(account.account_info_ids[0].id)
                account_info.account_id = False
            # set new reference
            account.account_info_id.account_id = account

    def _search_info(self, operator, value):
        return []

    def write(self, values):
        res = super(IapAccount, self).write(values)
        iap_edits = ['warn_me', 'warning_threshold', 'warning_email']
        if any(edited_attribute in values for edited_attribute in iap_edits):
            try:
                route = '/iap/update-warning-odoo'
                endpoint = iap_tools.iap_get_endpoint(self.env)
                url = endpoint + route
                data = {
                    'account_token': self.mapped('account_token')[0],
                    'dbuuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
                    'warn_me': values.get('warn_me'),
                    'warning_threshold': values.get('warning_threshold'),
                    'warning_email': values.get('warning_email'),
                }
                iap_tools.iap_jsonrpc(url=url, params=data)
            except AccessError as e:
                _logger.warning('Save service error : %s', str(e))
        return res

    def get_services(self):
        try:
            route = '/iap/services-token'
            endpoint = iap_tools.iap_get_endpoint(self.env)
            url = endpoint + route
            account_tokens = self.env['iap.account'].sudo().search([]).mapped('account_token')
            params = {
                'dbuuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
                'iap_accounts': account_tokens,
            }
            services = iap_tools.iap_jsonrpc(url=url, params=params)
            for service in services:
                account_id = self.env['iap.account'].sudo().search(
                    [('account_token', '=', service['account_token'])]).ids[0]
                service['account_id'] = account_id
                self.env['iap.account.info'].create(service)
        except AccessError as e:
            _logger.warning('Get services error : %s', str(e))

    @api.model_create_multi
    def create(self, vals_list):
        accounts = super().create(vals_list)
        if self.env['ir.config_parameter'].sudo().get_param('database.is_neutralized'):
            # Disable new accounts on a neutralized database
            for account in accounts:
                account.account_token = f"{account.account_token.split('+')[0]}+disabled"
        return accounts

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
                self.env.flush_all()
                IapAccount = self.with_env(self.env(cr=cr))
                # Need to use sudo because regular users do not have delete right
                IapAccount.search(domain + [('account_token', '=', False)]).sudo().unlink()
                accounts = accounts - accounts_without_token
        if not accounts:
            if hasattr(threading.current_thread(), 'testing') and threading.current_thread().testing:
                # During testing, we don't want to commit the creation of a new IAP account to the database
                return self.create({'service_name': service_name})

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
    def get_credits_url(self, service_name, base_url='', credit=0, trial=False, account_token=False):
        """ Called notably by ajax crash manager, buy more widget, partner_autocomplete, sanilmail. """
        dbuuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        if not base_url:
            endpoint = iap_tools.iap_get_endpoint(self.env)
            route = '/iap/1/credit'
            base_url = endpoint + route
        if not account_token:
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

    def action_buy_credits(self):
        for account in self:
            return {
                'type': 'ir.actions.act_url',
                'url': self.env['iap.account'].get_credits_url(
                    account_token=account.account_token,
                    service_name=account.service_name,
                ),
            }

    def action_toggle_show_token(self):
        for account in self:
            account.show_token = not account.show_token
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
            except AccessError as e:
                _logger.info('Get credit error : %s', str(e))
                credit = -1

        return credit


class IAPAccountInfo(models.TransientModel):
    _name = 'iap.account.info'
    _description = 'IAP Account Info'
    _transient_max_hours = 1

    account_id = fields.Many2one('iap.account', string='IAP Account')
    account_token = fields.Char()
    balance = fields.Float(string='Balance', digits=(16, 4), default=0)
    account_uuid_hashed = fields.Char(string='Account UUID')
    service_name = fields.Char(string='Related Service')
    description = fields.Char()
    warn_me = fields.Boolean('Warn me', default=False)
    warning_threshold = fields.Float('Threshold')
    warning_email = fields.Char()
    unit_name = fields.Char(default='Credits')
