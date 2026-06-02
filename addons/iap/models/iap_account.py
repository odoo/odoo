# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import logging
import secrets
import uuid
from urllib.parse import urlencode
import werkzeug.urls
from requests import RequestException

from odoo import api, fields, models, _
from odoo.addons.iap.tools import iap_tools
from odoo.exceptions import UserError
from odoo.modules import module
from odoo.tools.urls import urljoin as url_join

from odoo import Command

_logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = 'https://iap.odoo.com'


class IapAccount(models.Model):
    _name = 'iap.account'
    _description = 'IAP Account'

    name = fields.Char()
    service_id = fields.Many2one('iap.service', required=True)
    service_name = fields.Char(related='service_id.technical_name')
    service_price_description = fields.Char(related='service_id.price_description')
    service_locked = fields.Boolean(default=False)  # If True, the service can't be edited anymore
    description = fields.Char(related='service_id.description')
    account_token = fields.Char(
        default=lambda s: uuid.uuid4().hex,
        help="Account token is your authentication key for this service. Do not share it.",
        size=43,
        copy=False,
        groups="base.group_system",
    )
    company_ids = fields.Many2many('res.company')

    # Dynamic fields, which are received from iap server and set when loading the view
    balance_amount = fields.Float()
    balance = fields.Char(compute='_compute_balance')
    state = fields.Selection([('banned', 'Banned'), ('registered', "Registered"), ('unregistered', "Unregistered")], readonly=True)

    @api.depends('balance_amount', 'service_id.integer_balance', 'service_id.unit_name')
    def _compute_balance(self):
        for account in self:
            balance_amount = round(account.balance_amount, None if account.service_id.integer_balance else 4)
            account.balance = f"{balance_amount} {account.service_id.unit_name or ''}"

    def web_read(self, *args, **kwargs):
        self._get_account_information_from_iap()
        return super().web_read(*args, **kwargs)

    def action_manage(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': self.get_credits_url(self.service_name, self.account_token),
            'target': 'new',
        }

    def _get_account_information_from_iap(self):
        # During testing, we don't want to call the iap server
        if module.current_test:
            return
        route = '/iap/1/get-accounts-information'
        endpoint = iap_tools.iap_get_endpoint(self.env)
        url = url_join(endpoint, route)
        params = {
            'iap_accounts': [{
                'token': account.sudo().account_token,
                'service': account.service_id.technical_name,
            } for account in self if account.service_id],
            'dbuuid': self.env['ir.config_parameter'].sudo().get_str('database.uuid'),
        }
        try:
            accounts_information = iap_tools.iap_jsonrpc(url=url, params=params)
        except RequestException as e:
            _logger.warning("Fetch of the IAP accounts information has failed: %s", str(e))
            raise UserError(self.env._("The IAP server is unreachable and the information may not be up to date.\nPlease try again later."))

        for token, information in accounts_information.items():
            information.pop('link_to_service_page', None)
            accounts = self.filtered(lambda acc: secrets.compare_digest(acc.sudo().account_token, token))
            for account in accounts:
                # Default rounding of 4 decimal places to avoid large decimals
                account_info = self._get_account_info(account, information)

                account = account.with_context(disable_iap_update=True)
                account.write(account_info)

                service_information = information.get("service", {})
                self.env['iap.service.pack'].search([('service_id', '=', account.service_id.id)]).unlink()
                account.service_id.write({
                    "description": service_information.get("description", ""),
                    "price_description": service_information.get("price_description", ""),
                    "pack_ids": [Command.create({
                        "name": pack["name"],
                        "credit": pack["credit"],
                        "price": pack["price"],
                        "service_id": account.service_id.id,
                        "iap_service_pack_identifier": pack["id"],
                    }) for pack in service_information.get("packs", [])],
                })

    def _get_account_info(self, account_id, information):
        return {
            'balance_amount': information['balance'],
            'state': information['registered'],
            'service_locked': True,  # The account exist on IAP, prevent the edition of the service
        }

    @api.model_create_multi
    def create(self, vals_list):
        accounts = super().create(vals_list)
        for account in accounts:
            if not account.name:
                account.name = account.service_id.name

        if self.env['ir.config_parameter'].sudo().get_bool('database.is_neutralized'):
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
        accounts_without_token = accounts.filtered(lambda acc: not acc.sudo().account_token)
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
                raise UserError(self.env._("No service exists with the provided technical name"))
            if module.current_test:
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
                account_token = account.sudo().account_token
            account = self.browse(account.id)
            account._fields['account_token']._update_cache(account, account_token)
            return account
        accounts_with_company = accounts.filtered(lambda acc: acc.company_ids)
        if accounts_with_company:
            return accounts_with_company[0]
        return accounts[0]

    @api.model
    def get_account_id(self, service_name):
        return self.get(service_name).id

    @api.model
    def get_credits_url(self, service_name, account_token=None):
        """ Called notably by: buy more widget, partner_autocomplete, snailmail, ... """
        dbuuid = self.env['ir.config_parameter'].sudo().get_str('database.uuid')
        endpoint = iap_tools.iap_get_endpoint(self.env)
        route = '/iap/1/my_account'
        base_url = url_join(endpoint, route)
        account_token = account_token or self.get(service_name).sudo().account_token
        hashed_account_token = self._hash_iap_token(account_token)
        d = {
            'dbuuid': dbuuid,
            'service_name': service_name,
            'account_token': hashed_account_token,
            'hashed': 1,
        }
        return '%s?%s' % (base_url, werkzeug.urls.url_encode(d))

    @api.model
    def _hash_iap_token(self, key):
        # disregard possible suffix
        key = (key or '').split('+')[0]
        if not key:
            raise UserError(_('The IAP token provided is invalid or empty.'))
        return hashlib.sha1(key.encode('utf-8')).hexdigest()

    def action_buy_credits(self):
        return {
            'type': 'ir.actions.act_url',
            'url': self.env['iap.account'].get_credits_url(
                account_token=self.sudo().account_token,
                service_name=self.service_name,
            ),
        }

    def action_open_iap_account(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'self',
        }

    @api.model
    def action_view_my_services(self):
        endpoint = iap_tools.iap_get_endpoint(self.env)
        account_tokens = self.env["iap.account"].search([]).mapped("account_token")
        params = {
            "db_uuid": self.env['ir.config_parameter'].sudo().get_str('database.uuid'),
            "account_tokens": ",".join(self.env['iap.account']._hash_iap_token(token) for token in account_tokens),
            "hashed": 1,
        }
        url = endpoint + "/iap/1/all-in-app-services?" + urlencode(params)
        return {
            "type": "ir.actions.act_url",
            "url": url,
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
            url = url_join(endpoint, route)
            params = {
                'dbuuid': self.env['ir.config_parameter'].sudo().get_str('database.uuid'),
                'account_token': account.sudo().account_token,
                'service_name': service_name,
            }
            try:
                credit = iap_tools.iap_jsonrpc(url=url, params=params)
            except RequestException as e:
                _logger.info('Get credit error : %s', str(e))
                credit = -1

        return credit
