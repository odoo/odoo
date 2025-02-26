# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import secrets
import threading
import uuid
import werkzeug.urls

from odoo import api, fields, models, _
from odoo.addons.iap.tools import iap_tools
from odoo.exceptions import AccessError, UserError
from odoo.tools import get_lang

_logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = 'https://iap.odoo.com'


class IapAccount(models.Model):
    _name = 'iap.account'
    _description = 'IAP Account'

    name = fields.Char()
    service_id = fields.Many2one('iap.service', required=True)
    service_name = fields.Char(related='service_id.technical_name')
    service_locked = fields.Boolean(default=False)  # If True, the service can't be edited anymore
    description = fields.Char(related='service_id.description')
    account_token = fields.Char(
        default=lambda s: uuid.uuid4().hex,
        help="Account token is your authentication key for this service. Do not share it.",
        size=43)
    company_ids = fields.Many2many('res.company')

    # Dynamic fields, which are received from iap server and set when loading the view
    balance = fields.Char(readonly=True)
    warning_threshold = fields.Float("Email Alert Threshold")
    warning_user_ids = fields.Many2many('res.users', string="Email Alert Recipients")
    state = fields.Selection([('banned', 'Banned'), ('registered', "Registered"), ('unregistered', "Unregistered")], readonly=True)

    @api.constrains('warning_threshold', 'warning_user_ids')
    def validate_warning_alerts(self):
        for account in self:
            if account.warning_threshold < 0:
                raise UserError(_("Please set a positive email alert threshold."))
            users_with_no_email = [user.name for user in self.warning_user_ids if not user.email]
            if users_with_no_email:
                raise UserError(_(
                    "One of the email alert recipients doesn't have an email address set. Users: %s",
                    ",".join(users_with_no_email),
                ))

    def web_read(self, *args, **kwargs):
        if not self.env.context.get('disable_iap_fetch'):
            self._get_account_information_from_iap()
        return super().web_read(*args, **kwargs)

    def web_save(self, *args, **kwargs):
        return super(IapAccount, self.with_context(disable_iap_fetch=True)).web_save(*args, **kwargs)

    def write(self, values):
        res = super().write(values)
        if (
            not self.env.context.get('disable_iap_update')
            and any(warning_attribute in values for warning_attribute in ('warning_threshold', 'warning_user_ids'))
        ):
            route = '/iap/1/update-warning-email-alerts'
            endpoint = iap_tools.iap_get_endpoint(self.env)
            url = werkzeug.urls.url_join(endpoint, route)
            for account in self:
                data = {
                    'account_token': account.account_token,
                    'warning_threshold': account.warning_threshold,
                    'warning_emails': [{
                        'email': user.email,
                        'lang_code': user.lang or get_lang(self.env).code,
                    } for user in account.warning_user_ids],
                }
                try:
                    iap_tools.iap_jsonrpc(url=url, params=data)
                except AccessError as e:
                    _logger.warning("Update of the warning email configuration has failed: %s", str(e))
        return res

    @staticmethod
    def is_running_test_suite():
        return hasattr(threading.current_thread(), 'testing') and threading.current_thread().testing

    def _get_account_information_from_iap(self):
        # During testing, we don't want to call the iap server
        if self.is_running_test_suite():
            return
        route = '/iap/1/get-accounts-information'
        endpoint = iap_tools.iap_get_endpoint(self.env)
        url = werkzeug.urls.url_join(endpoint, route)
        params = {
            'iap_accounts': [{
                'token': account.account_token,
                'service': account.service_id.technical_name,
            } for account in self if account.service_id],
            'dbuuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
        }
        try:
            accounts_information = iap_tools.iap_jsonrpc(url=url, params=params)
        except AccessError as e:
            _logger.warning("Fetch of the IAP accounts information has failed: %s", str(e))
            return

        for token, information in accounts_information.items():
            information.pop('link_to_service_page', None)
            accounts = self.filtered(lambda acc: secrets.compare_digest(acc.account_token, token))

            for account in accounts:
                # Default rounding of 4 decimal places to avoid large decimals
                balance_amount = round(information['balance'], None if account.service_id.integer_balance else 4)
                balance = f"{balance_amount} {account.service_id.unit_name or ''}"

                account_info = self._get_account_info(account, balance, information)
                account.with_context(disable_iap_update=True, tracking_disable=True).write(account_info)

    def _get_account_info(self, account_id, balance, information):
        return {
            'balance': balance,
            'warning_threshold': information['warning_threshold'],
            'state': information['registered'],
            'service_locked': True,  # The account exist on IAP, prevent the edition of the service
        }

    @api.model_create_multi
    def create(self, vals_list):
        accounts = super().create(vals_list)
        for account in accounts:
            if not account.name:
                account.name = account.service_id.name

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
            service = self.env['iap.service'].search([('technical_name', '=', service_name)], limit=1)
            if not service:
                raise UserError("No service exists with the provided technical name")
            if self.is_running_test_suite():
                # During testing, we don't want to commit the creation of a new IAP account to the database
                return self.sudo().create({'service_id': service.id})

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
                    account = IapAccount.create({'service_id': service.id})
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
    def get_account_id(self, service_name):
        return self.get(service_name).id

    @api.model
    def get_credits_url(self, service_name, base_url='', credit=0, trial=False, account_token=False):
        """ Called notably by ajax crash manager, buy more widget, partner_autocomplete, sanilmail. """
        dbuuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        if not base_url:
            endpoint = iap_tools.iap_get_endpoint(self.env)
            route = '/iap/1/credit'
            base_url = werkzeug.urls.url_join(endpoint, route)
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
        return {
            'type': 'ir.actions.act_url',
            'url': self.env['iap.account'].get_credits_url(
                account_token=self.account_token,
                service_name=self.service_name,
            ),
        }

    @api.model
    def get_config_account_url(self):
        """ Called notably by ajax partner_autocomplete. """
        account = self.env['iap.account'].get('partner_autocomplete')
        menu = self.env.ref('iap.iap_account_menu')
        if not self.env.user.has_group('base.group_no_one'):
            return False
        if account:
            url = f"/odoo/action-iap.iap_account_action/{account.id}?menu_id={menu.id}"
        else:
            url = f"/odoo/action-iap.iap_account_action?menu_id={menu.id}"
        return url

    @api.model
    def get_credits(self, service_name):
        account = self.get(service_name, force_create=False)
        credit = 0

        if account:
            route = '/iap/1/balance'
            endpoint = iap_tools.iap_get_endpoint(self.env)
            url = werkzeug.urls.url_join(endpoint, route)
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
