# -*- coding: utf-8 -*-

import base64
import datetime
import requests
import logging
import re
import uuid
import urllib.parse
import odoo
import odoo.release
from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from requests.exceptions import RequestException, Timeout, ConnectionError
from odoo import api, fields, models, modules, tools
from odoo.exceptions import UserError, CacheMiss, MissingError, ValidationError, RedirectWarning
from odoo.http import request
from odoo.addons.account_online_synchronization.models.odoofin_auth import OdooFinAuth
from odoo.tools.misc import format_amount, format_date, get_lang
from odoo.tools import _, LazyTranslate

_lt = LazyTranslate(__name__)
_logger = logging.getLogger(__name__)
pattern = re.compile("^[a-z0-9-_]+$")
runbot_pattern = re.compile(r"^https:\/\/[a-z0-9-_]+\.[a-z0-9-_]+\.odoo\.com$")

class OdooFinRedirectException(UserError):
    """ When we need to open the iframe in a given mode. """

    def __init__(self, message=_lt('Redirect'), mode='link'):
        self.mode = mode
        super().__init__(message)

class AccountOnlineAccount(models.Model):
    _name = 'account.online.account'
    _description = 'representation of an online bank account'

    name = fields.Char(string="Account Name", help="Account Name as provided by third party provider")
    online_identifier = fields.Char(help='Id used to identify account by third party provider', readonly=True)
    balance = fields.Float(readonly=True, help='Balance of the account sent by the third party provider')
    account_number = fields.Char(help='Set if third party provider has the full account number')
    account_data = fields.Char(help='Extra information needed by third party provider', readonly=True)

    account_online_link_id = fields.Many2one('account.online.link', readonly=True, ondelete='cascade')
    journal_ids = fields.One2many('account.journal', 'account_online_account_id', string='Journal', domain="[('type', 'in', ('bank', 'credit')), ('company_id', '=', company_id)]")
    last_sync = fields.Date("Last synchronization")
    company_id = fields.Many2one('res.company', related='account_online_link_id.company_id')
    currency_id = fields.Many2one('res.currency')
    fetching_status = fields.Selection(
        selection=[
            ('planned', 'Planned'), # When all the transactions couldn't be imported in one go and is waiting for next batch
            ('waiting', 'Waiting'),  # When waiting for the provider to fetch the transactions
            ('processing', 'Processing'),  # When currently importing in odoo
            ('done', 'Done'),  # When every transaction have been imported in odoo
        ]
    )

    inverse_balance_sign = fields.Boolean(
        string="Inverse Balance Sign",
        help="If checked, the balance sign will be inverted",
    )
    inverse_transaction_sign = fields.Boolean(
        string="Inverse Transaction Sign",
        help="If checked, the transaction sign will be inverted",
    )

    @api.constrains('journal_ids')
    def _check_journal_ids(self):
        for online_account in self:
            if len(online_account.journal_ids) > 1:
                raise ValidationError(_('You cannot have two journals associated with the same Online Account.'))

    @api.model_create_multi
    def create(self, vals):
        result = super().create(vals)
        if any(data.get('fetching_status') in {'waiting', 'processing', 'planned'} for data in vals):
            self.env['account.journal']._toggle_asynchronous_fetching_cron()
        return result

    def write(self, vals):
        result = super().write(vals)
        if vals.get('fetching_status') in {'waiting', 'processing', 'planned'}:
            self.env['account.journal']._toggle_asynchronous_fetching_cron()
        return result

    def unlink(self):
        result = super().unlink()
        self.env['account.journal']._toggle_asynchronous_fetching_cron()
        return result

    def _assign_journal(self, swift_code=False):
        """
        This method allows to link an online account to a journal with the following heuristics
        Also, Create and assign bank & swift/bic code if odoofin returns one
        If a journal is present in the context (active_model = account.journal and active_id), we assume that
        We started the journey from a journal and we assign the online_account to that particular journal.
        Otherwise we will create a new journal on the fly and assign the online_account to it.
        If an online_account was previously set on the journal, it will be removed and deleted.
        This will also set the 'online_sync' source on the journal and create an activity for the consent renewal
        The date to fetch transaction will also be set and have the following value:
            date of the latest statement line on the journal
            or date of the fiscalyear lock date
            or False (we fetch transactions as far as possible)
        """
        currency_id = self.currency_id.id if not self.currency_id.is_current_company_currency else False
        existing_journal = self.env['account.journal'].search([
            ('bank_acc_number', '=', self.account_number),
            ('currency_id', '=', currency_id),
            ('type', '=', 'bank'),
            ('account_online_account_id', '=', False),
        ], limit=1)

        self.ensure_one()
        if (active_id := self.env.context.get('active_id')) and self.env.context.get('active_model') == 'account.journal':
            journal = self.env['account.journal'].browse(active_id)
            # If we already have a linked account on that journal, it means we are in the process of relinking
            # it is due to an error that occured which require to redo the connection (can't fix it).
            # Hence we delete the previously linked account.online.link to prevent showing multiple
            # duplicate existing connections when opening the iframe
            if journal.account_online_link_id:
                journal.account_online_link_id.unlink()

            # Ensure the journal's currency matches the bank account's currency.
            if self.currency_id.id != journal.currency_id.id:
                # If the journal already has entries in a different currency, raise an error.
                statement_lines_in_other_currency = self.env['account.bank.statement.line'].search_count([
                    ('journal_id', '=', journal.id),
                    ('currency_id', 'not in', (False, self.currency_id.id)),
                ], limit=1)
                if statement_lines_in_other_currency:
                    raise UserError(_("Journal %(journal_name)s has been set up with a different currency and already has existing entries. "
                                      "You can't link selected bank account in %(currency_name)s to it",
                                      journal_name=journal.name, currency_name=self.currency_id.name))
                else:
                    # If the journal's default bank account has entries in a differente currency, silently do nothing to avoid an error.
                    move_lines_in_other_currency = self.env['account.move.line'].search_count([
                        ('account_id', '=', journal.default_account_id.id),
                        ('currency_id', '!=', self.currency_id.id),
                    ], limit=1)
                    if not move_lines_in_other_currency:
                        # If not set yet and there are no conflicting entries, set it.
                        journal.sudo().currency_id = self.currency_id.id
        elif existing_journal:
            journal = existing_journal
        else:
            journal = self.env['account.journal'].create({
                'name': self.account_number or self.display_name,
                'code': self.env['account.journal'].get_next_bank_cash_default_code('bank', self.env.company),
                'type': 'bank',
                'company_id': self.env.company.id,
                'currency_id': currency_id,
            })

        self.sudo().journal_ids = journal

        journal_vals = {
            'bank_statements_source': 'online_sync',
        }
        if self.account_number and not self.journal_ids.bank_acc_number:
            journal_vals['bank_acc_number'] = self.account_number
        self.journal_ids.sudo().write(journal_vals)
        # Update connection status and get consent expiration date and create an activity on related journal
        self.account_online_link_id._update_connection_status()

        # Set last_sync date (date of latest statement or one day after accounting lock date or False)
        lock_date = self.env.company._get_user_fiscal_lock_date(journal)
        last_sync = lock_date + relativedelta(days=1) if lock_date and lock_date > datetime.date.min else None
        bnk_stmt_line = self.env['account.bank.statement.line'].search([('journal_id', 'in', self.journal_ids.ids)], order="date desc", limit=1)
        if bnk_stmt_line:
            last_sync = bnk_stmt_line.date
        self.last_sync = last_sync

        if swift_code:
            if self.journal_ids.bank_account_id.bank_id:
                if not self.journal_ids.bank_account_id.bank_id.bic:
                    self.journal_ids.bank_account_id.bank_id.bic = swift_code
            else:
                bank_rec = self.env['res.bank'].search([('bic', '=', swift_code)], limit=1)
                if not bank_rec:
                    bank_rec = self.env['res.bank'].create({'name': self.account_online_link_id.display_name, 'bic': swift_code})
                self.journal_ids.bank_account_id.bank_id = bank_rec.id

    def _refresh(self):
        """
            This method is called on an online_account in order to check the current refresh status of the
            account. If we are in manual mode and if the provider allows it, this will also trigger a
            manual refresh on the provider side. Call to /proxy/v1/refresh will return a boolean
            telling us if the refresh was successful or not. When not successful, we should avoid
            trying to fetch transactions. Cases where we can receive an unsuccessful response are as follow
            (non exhaustive list)
            - Another refresh was made too early and provider/bank limit the number of refresh allowed
            - Provider is in the process of importing the transactions so we should wait until he has
                finished before fetching them in Odoo
            :return: True if provider has refreshed the account and we can start fetching transactions
        """
        data = {'account_id': self.online_identifier}
        while True:
            # While this is kind of a bad practice to do, it can happen that provider_data/account_data change between
            # 2 calls, the reason is that those field contains the encrypted information needed to access the provider
            # and first call can result in an error due to the encrypted token inside provider_data being expired for example.
            # In such a case, we renew the token with the provider and send back the newly encrypted token inside provider_data
            # which result in the information having changed, henceforth why those fields are passed at every loop.
            data.update({
                'provider_data': self.account_online_link_id.provider_data,
                'account_data': self.account_data,
                'fetching_status': self.fetching_status,
            })
            resp_json = self.account_online_link_id._fetch_odoo_fin('/proxy/v1/refresh', data=data)
            if resp_json.get('account_data'):
                self.account_data = resp_json['account_data']
            currently_fetching = resp_json.get('currently_fetching')
            success = resp_json.get('success', True)
            if currently_fetching:
                # Provider has not finished fetching transactions, set status to waiting
                self.fetching_status = 'waiting'
            if not resp_json.get('next_data'):
                break
            data['next_data'] = resp_json.get('next_data') or {}
        return {'success': not currently_fetching and success, 'data': resp_json.get('data', {})}

    def _retrieve_transactions(self, date=None, include_pendings=False):
        last_stmt_line = self.env['account.bank.statement.line'].search([
                ('date', '<=', self.last_sync or fields.Date().today()),
                ('online_transaction_identifier', '!=', False),
                ('journal_id', 'in', self.journal_ids.ids),
                ('online_account_id', '=', self.id)
            ], order="date desc", limit=1)
        transactions = []

        start_date = date or last_stmt_line.date or self.last_sync
        data = {
            # If we are in a new sync, we do not give a start date; We will fetch as much as possible. Otherwise, the last sync is the start date.
            'start_date': start_date and format_date(self.env, start_date, date_format='yyyy-MM-dd'),
            'account_id': self.online_identifier,
            'last_transaction_identifier': last_stmt_line.online_transaction_identifier if not include_pendings else None,
            'currency_code': self.currency_id.name or self.journal_ids[0].currency_id.name or self.company_id.currency_id.name,
            'include_pendings': include_pendings,
            'include_foreign_currency': True,
        }
        pendings = []
        while True:
            # While this is kind of a bad practice to do, it can happen that provider_data/account_data change between
            # 2 calls, the reason is that those field contains the encrypted information needed to access the provider
            # and first call can result in an error due to the encrypted token inside provider_data being expired for example.
            # In such a case, we renew the token with the provider and send back the newly encrypted token inside provider_data
            # which result in the information having changed, henceforth why those fields are passed at every loop.
            data.update({
                'provider_data': self.account_online_link_id.provider_data,
                'account_data': self.account_data,
            })
            resp_json = self.account_online_link_id._fetch_odoo_fin('/proxy/v1/transactions', data=data)
            if resp_json.get('balance'):
                sign = -1 if self.inverse_balance_sign else 1
                self.balance = sign * resp_json['balance']
            if resp_json.get('account_data'):
                self.account_data = resp_json['account_data']
            transactions += resp_json.get('transactions', [])
            pendings += resp_json.get('pendings', [])
            if not resp_json.get('next_data'):
                break
            data['next_data'] = resp_json.get('next_data') or {}

        return {
            'transactions': self._format_transactions(transactions),
            'pendings': self._format_transactions(pendings),
        }

    def get_formatted_balances(self):
        balances = {}
        for account in self:
            if account.currency_id:
                formatted_balance = format_amount(self.env, account.balance, account.currency_id)
            else:
                formatted_balance = '%.2f' % account.balance
            balances[account.id] = [formatted_balance, account.balance]
        return balances

    ###########
    # HELPERS #
    ###########

    def _get_filtered_transactions(self, new_transactions):
        """ This function will filter transaction to avoid duplicate transactions.
            To do that, we're comparing the received online_transaction_identifier with
            those in the database. If there is a match, the new transaction is ignored.
        """
        self.ensure_one()

        journal_id = self.journal_ids[0]
        existing_bank_statement_lines = self.env['account.bank.statement.line'].search_fetch(
            [
                ('journal_id', '=', journal_id.id),
                ('online_transaction_identifier', 'in', [
                    transaction['online_transaction_identifier']
                    for transaction in new_transactions
                    if transaction.get('online_transaction_identifier')
                ]),
            ],
            ['online_transaction_identifier']
        )
        existing_online_transaction_identifier = set(existing_bank_statement_lines.mapped('online_transaction_identifier'))

        filtered_transactions = []
        # Remove transactions already imported in Odoo
        for transaction in new_transactions:
            if transaction_identifier := transaction['online_transaction_identifier']:
                if transaction_identifier in existing_online_transaction_identifier:
                    continue
                existing_online_transaction_identifier.add(transaction_identifier)

            filtered_transactions.append(transaction)
        return filtered_transactions

    def _format_transactions(self, new_transactions):
        """ This function format transactions:
            It will:
             - Replace the foreign currency code with the corresponding currency id and activating the currencies that are not active
             - Change inverse the transaction sign if the setting is activated
             - Parsing the date
             - Setting the account online account and the account journal
        """
        self.ensure_one()
        transaction_sign = -1 if self.inverse_transaction_sign else 1
        currencies = self.env['res.currency'].with_context(active_test=False).search([])
        currency_code_mapping = {currency.name: currency for currency in currencies}

        formatted_transactions = []
        for transaction in new_transactions:
            if transaction.get('foreign_currency_code'):
                currency = currency_code_mapping.get(transaction.pop('foreign_currency_code'))
                if currency:
                    transaction.update({'foreign_currency_id': currency.id})
                    if not currency.active:
                        currency.active = True

            formatted_transactions.append({
                **transaction,
                'amount': transaction['amount'] * transaction_sign,
                'date': fields.Date.from_string(transaction['date']),
                'online_account_id': self.id,
                'journal_id': self.journal_ids[0].id,
                'company_id': self.company_id.id,
            })
        return formatted_transactions

    def action_reset_fetching_status(self):
        """
            This action will reset the fetching status to avoid the problem when there is an error during the
            synchronisation that would block the customer with his connection since we block the fetch due that value.
            With this he has a button that can reset the fetching status.
        """
        self.fetching_status = None


class AccountOnlineLink(models.Model):
    _name = 'account.online.link'
    _description = 'Bank Connection'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _compute_next_synchronization(self):
        for rec in self:
            rec.next_refresh = self.env['ir.cron'].sudo().search([('id', '=', self.env.ref('account_online_synchronization.online_sync_cron').id)], limit=1).nextcall

    account_online_account_ids = fields.One2many('account.online.account', 'account_online_link_id')
    last_refresh = fields.Datetime(readonly=True, default=fields.Datetime.now)
    next_refresh = fields.Datetime("Next synchronization", compute='_compute_next_synchronization')
    state = fields.Selection([('connected', 'Connected'), ('error', 'Error'), ('disconnected', 'Not Connected')],
                             default='disconnected', tracking=True, required=True, readonly=True)
    connection_state_details = fields.Json()
    auto_sync = fields.Boolean(
        default=True,
        string="Automatic synchronization",
        help="""If possible, we will try to automatically fetch new transactions for this record
                \nIf the automatic sync is disabled. that will be due to security policy on the bank's end. So, they have to launch the sync manually""",
    )
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    has_unlinked_accounts = fields.Boolean(default=True, help="True if that connection still has accounts that are not linked to an Odoo journal")
    show_sync_actions = fields.Boolean(compute='_compute_show_sync_actions')

    # Information received from OdooFin, should not be tampered with
    name = fields.Char(help="Institution Name", readonly=True)
    client_id = fields.Char(help="Represent a link for a given user towards a banking institution", readonly=True)
    refresh_token = fields.Char(help="Token used to sign API request, Never disclose it",
                                readonly=True, groups="base.group_system")
    access_token = fields.Char(help="Token used to access API.", readonly=True, groups="account.group_account_basic")
    provider_data = fields.Char(help="Information needed to interact with third party provider", readonly=True)
    expiring_synchronization_date = fields.Date(help="Date when the consent for this connection expires",
                                                readonly=True)
    journal_ids = fields.One2many('account.journal', compute='_compute_journal_ids')
    provider_type = fields.Char(help="Third Party Provider", readonly=True)

    ###################
    # Compute methods #
    ###################

    @api.depends('account_online_account_ids')
    def _compute_journal_ids(self):
        for online_link in self:
            online_link.journal_ids = online_link.account_online_account_ids.journal_ids

    @api.depends('company_id')
    @api.depends_context('allowed_company_ids')
    def _compute_show_sync_actions(self):
        for online_link in self:
            online_link.show_sync_actions = online_link.company_id in self.env.companies

    ##########################
    # Wizard opening actions #
    ##########################
    def create_new_bank_account_action(self, data=None):
        self.ensure_one()
        # We do return the bank account setup wizard if we don't have minimum info
        if not data or not data.get('account_number'):
            ctx = self.env.context
            # if this was called from kanban box, active_model is in context
            if ctx.get('active_model') == 'account.journal':
                ctx = {**ctx, 'default_linked_journal_id': ctx.get('active_id', False), 'dialog_size': 'medium'}
            return {
                'type': 'ir.actions.act_window',
                'name': _('Setup Bank Account'),
                'res_model': 'account.setup.bank.manual.config',
                'target': 'new',
                'view_mode': 'form',
                'context': ctx,
                'views': [(False, 'form')],
            }

        bank = self.env['res.bank']
        if data.get('name'):
            bank = self.env['res.bank'].sudo().create({
                'name': data['name'],
                'bic': data.get('swift_code'),
            })

        bank_account = self.env['res.partner.bank']._find_or_create_bank_account(
            account_number=data.get('account_number'),
            partner=self.company_id.partner_id, allow_company_account_creation=True,
            company=self.company_id,
            extra_create_vals={'bank_id': bank.id},
        )

        self.env['account.journal'].sudo().create({
            'name': data.get('account_number'),
            'type': data.get('journal_type') or 'bank',
            'bank_account_id': bank_account.id,
        })

        return {'type': 'ir.actions.client', 'tag': 'soft_reload'}

    def _link_accounts_to_journals_action(self, swift_code):
        """
        This method opens a wizard allowing the user to link
        his bank accounts with new or existing journal.
        :return: An action openning a wizard to link bank accounts with account journal.
        """
        self.ensure_one()
        account_bank_selection_wizard = self.env['account.bank.selection'].create({
            'account_online_link_id': self.id,
        })

        return {
            "name": _("Select a Bank Account"),
            "type": "ir.actions.act_window",
            "res_model": "account.bank.selection",
            "views": [[False, "form"]],
            "target": "new",
            "res_id": account_bank_selection_wizard.id,
            'context': dict(self.env.context, swift_code=swift_code),
        }

    @api.model
    def _show_fetched_transactions_action(self, stmt_line_ids, duplicates_from_date):
        return self.env['account.bank.statement.line']._action_open_bank_reconciliation_widget(
            extra_domain=[('id', 'in', stmt_line_ids.ids)],
            name=_('Fetched Transactions'),
            **({'default_context': {'duplicates_from_date': duplicates_from_date}} if duplicates_from_date else {}),
        )

    def _get_connection_state_details(self, journal):
        self.ensure_one()
        if self.connection_state_details and self.connection_state_details.get(str(journal.id)):
            # We have to check that we have a key and a right value for this journal
            # Because if we have an empty dict, the JS part will handle it as a Proxy object.
            # To avoid that, we checked if we have a key in the dict and if the value is truthy.
            return self.connection_state_details[str(journal.id)]
        return None

    def _pop_connection_state_details(self, journal):
        self.ensure_one()
        if journal_connection_state_details := self._get_connection_state_details(journal):
            self._set_connection_state_details(journal, {})
            return journal_connection_state_details
        return None

    def _set_connection_state_details(self, journal, connection_state_details):
        self.ensure_one()
        existing_connection_state_details = self.connection_state_details or {}
        self.connection_state_details = {
            **existing_connection_state_details,
            str(journal.id): connection_state_details,
        }

    def _notify_connection_update(self, journal, connection_state_details):
        """ The aim of this function is saving the last connection state details
            (like if the status is success or in error) on the account.online.link
            object. At the same moment, we're sending a websocket message to
            accounting dashboard where we return the status of the connection.
            To make sure that we don't return sensitive information, we filtered
            the connection state details to only send by websocket information
            like the connection status, how many transactions we fetched, and
            the error type. In case of an error, the function is calling rollback
            on the cursor and is committing the save on the account online link.
            It's also usefull to commit in case of error to send the websocket message.
            The commit is only called if we aren't in test mode and if the connection is
            in error.

            :param journal: The journal for which we want to save the connection state details.
            :param connection_state_details: The information about the status of the connection (like how many transactions fetched, ...)
        """
        self.ensure_one()

        connection_state_details_status = connection_state_details['status']  # We're always waiting for a status in the dict.
        if connection_state_details_status == 'error':
            # In case the connection status is in error, we roll back everything before saving the status.
            self.env.cr.rollback()
        if not (connection_state_details_status == 'success' and connection_state_details.get('nb_fetched_transactions', 0) == 0):
            self._set_connection_state_details(
                journal=journal,
                connection_state_details=connection_state_details,
            )
        self.env.ref('account.group_account_user').users._bus_send(
            'online_sync',
            {
                'id': journal.id,
                'connection_state_details': {
                    key: value
                    for key, value in connection_state_details.items()
                    if key in ('status', 'error_type', 'nb_fetched_transactions')
                },
            },
        )
        if connection_state_details_status == 'error' and not tools.config['test_enable'] and not modules.module.current_test:
            # In case the status is in error, and we aren't in test mode, we commit to save the last connection state and to send the websocket message
            self.env.cr.commit()

    def _handle_odoofin_redirect_exception(self, mode='link'):
        if mode == 'link':
            return self.with_context({'redirect_reconnection': True}).action_new_synchronization()
        return self.with_context({'redirect_reconnection': True})._open_iframe(mode=mode)

    #######################################################
    # Generic methods to contact server and handle errors #
    #######################################################

    @api.model
    def _get_odoofin_url(self, url):
        proxy_mode = self.env['ir.config_parameter'].sudo().get_param('account_online_synchronization.proxy_mode') or 'production'
        if not pattern.match(proxy_mode) and not runbot_pattern.match(proxy_mode):
            raise UserError(_('Invalid value for proxy_mode config parameter.'))
        endpoint_url = 'https://%s.odoofin.com%s' % (proxy_mode, url)
        if runbot_pattern.match(proxy_mode):
            endpoint_url = '%s%s' % (proxy_mode, url)
        return endpoint_url

    def _fetch_odoo_fin(self, url, data=None, ignore_status=False):
        """
        Method used to fetch data from the Odoo Fin proxy.
        :param url: Proxy's URL end point.
        :param data: HTTP data request.
        :return: A dict containing all data.
        """
        if not data:
            data = {}
        if self.state == 'disconnected' and not ignore_status:
            raise UserError(_('Please reconnect your online account.'))
        if not url.startswith('/'):
            raise UserError(_('Invalid URL'))

        timeout = int(self.env['ir.config_parameter'].sudo().get_param('account_online_synchronization.request_timeout')) or 60
        endpoint_url = self._get_odoofin_url(url)
        cron = self.env.context.get('cron', False)
        data['utils'] = {
            'request_timeout': timeout,
            'lang': get_lang(self.env).code,
            'server_version': odoo.release.serie,
            'db_uuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
            'cron': cron,
        }
        if request:
            # many banking institutions require the end-user IP/user_agent for traceability
            # of client-initiated actions. It won't be stored on odoofin side.
            data['utils']['psu_info'] = {
                'ip': request.httprequest.remote_addr,
                'user_agent': request.httprequest.user_agent.string,
            }

        try:
            # We have to use sudo to pass record as some fields are protected from read for common users.
            resp = requests.post(url=endpoint_url, json=data, timeout=timeout, auth=OdooFinAuth(record=self.sudo()))
            resp_json = resp.json()
            return self._handle_response(resp_json, url, data, ignore_status)
        except (Timeout, ConnectionError, RequestException, ValueError):
            _logger.warning('synchronization error')
            raise UserError(
                _("The online synchronization service is not available at the moment. "
                  "Please try again later."))

    def _handle_response(self, resp_json, url, data, ignore_status=False):
        # Response is a json-rpc response, therefore data is encapsulated inside error in case of error
        # and inside result in case of success.
        if not resp_json.get('error'):
            result = resp_json.get('result')
            state = result.get('odoofin_state') or False
            message = result.get('display_message') or False
            subject = message and _('Message') or False
            self._log_information(state=state, message=message, subject=subject)
            if result.get('provider_data'):
                # Provider_data is extremely important and must be saved as soon as we received it
                # as it contains encrypted credentials from external provider and if we loose them we
                # loose access to the bank account, As it is possible that provider_data
                # are received during a transaction containing multiple calls to the proxy, we ensure
                # that provider_data is committed in database as soon as we received it.
                self.provider_data = result.get('provider_data')
                self.env.cr.commit()
            return result
        else:
            error = resp_json.get('error')
            # Not considered as error
            if error.get('code') == 101:  # access token expired, not an error
                self._get_access_token()
                return self._fetch_odoo_fin(url, data, ignore_status)
            elif error.get('code') == 102:  # refresh token expired, not an error
                self._get_refresh_token()
                self._get_access_token()
                # We need to commit here because if we got a new refresh token, and a new access token
                # It means that the token is active on the proxy and any further call resulting in an
                # error would lose the new refresh_token hence blocking the account ad vitam eternam
                self.env.cr.commit()
                if self.journal_ids:  # We can't do it unless we already have a journal
                    self._update_connection_status()
                return self._fetch_odoo_fin(url, data, ignore_status)
            elif error.get('code') == 300:  # redirect, not an error
                raise OdooFinRedirectException(mode=error.get('data', {}).get('mode', 'link'))
            # If we are in the process of deleting the record ignore code 100 (invalid signature), 104 (account deleted)
            # 106 (provider_data corrupted) and allow user to delete his record from this side.
            elif error.get('code') in (100, 104, 106) and self.env.context.get('delete_sync'):
                return {'delete': True}
            # Log and raise error
            error_details = error.get('data')
            subject = error.get('message')
            message = error_details.get('message')
            state = error_details.get('odoofin_state') or 'error'
            ctx = self.env.context.copy()
            ctx['error_reference'] = error_details.get('error_reference')
            ctx['provider_type'] = error_details.get('provider_type')
            ctx['redirect_warning_url'] = error_details.get('redirect_warning_url')

            self.with_context(ctx)._log_information(state=state, subject=subject, message=message, reset_tx=True)

    def _log_information(self, state, subject=None, message=None, reset_tx=False):
        # If the reset_tx flag is passed, it means that we have an error, and we want to log it on the record
        # and then raise the error to the end user. To do that we first roll back the current transaction,
        # then we write the error on the record, we commit those changes, and finally we raise the error.
        if reset_tx:
            self.env.cr.rollback()
        try:
            # if state is disconnected, and new state is error: ignore it
            if state == 'error' and self.state == 'disconnected':
                state = 'disconnected'
            if state and self.state != state:
                self.write({'state': state})
            if state in ('error', 'disconnected'):
                self.account_online_account_ids.fetching_status = 'done'
            if reset_tx:
                context = self.env.context
                button_label = url = None
                if subject and message:
                    message_post = message
                    error_reference = context.get('error_reference')
                    provider = context.get('provider_type')
                    odoo_help_description = f'''ClientID: {self.client_id}\nInstitution: {self.name}\nError Reference: {error_reference}\nError Message: {message_post}\n'''
                    odoo_help_summary = f'Bank sync error ref: {error_reference} - Provider: {provider} - Client ID: {self.client_id}'
                    if context.get('redirect_warning_url'):
                        if context['redirect_warning_url'] == 'odoo_support':
                            url_params = urllib.parse.urlencode({'stage': 'bank_sync', 'summary': odoo_help_summary, 'description': odoo_help_description[:1500]})
                            url = f'https://www.odoo.com/help?{url_params}'
                            message += _("\n\nIf you've already opened a ticket for this issue, don't report it again: a support agent will contact you shortly.")
                            message_post = Markup('%s<br>%s <a href="%s" >%s</a>') % (message, _("You can contact Odoo support"), url, _("Here"))
                            button_label = _('Report issue')
                        else:
                            url = "https://www.odoo.com/documentation/18.0/applications/finance/accounting/bank/bank_synchronization.html#faq"
                            message_post = Markup('%s<br>%s <a href="%s" >%s</a>') % (message_post, _("Check the documentation"), url, _("Here"))
                            button_label = _('Check the documentation')
                    self.message_post(body=message_post, subject=subject)
                # In case of reset_tx, we commit the changes in order to have the message post saved
                self.env.cr.commit()
                # and then raise either a redirectWarning error so that customer can easily open an issue with Odoo,
                # or eventually bring the user to the documentation if there's no need to contact the support.
                if url:
                    action_id = {
                        "type": "ir.actions.act_url",
                        "url": url,
                    }
                    raise RedirectWarning(message, action_id, button_label) #pylint: disable=E0601
                # either a userError if there's no need to bother the support, or link to the doc.
                raise UserError(message)
        except (CacheMiss, MissingError):
            # This exception can happen if record was created and rollbacked due to error in same transaction
            # Therefore it is not possible to log information on it, in this case we just ignore it.
            pass

    ###############
    # API methods #
    ###############

    def _get_access_token(self):
        for link in self:
            resp_json = link._fetch_odoo_fin('/proxy/v1/get_access_token', ignore_status=True)
            link.access_token = resp_json.get('access_token', False)

    def _get_refresh_token(self):
        # Use sudo as refresh_token field is not accessible to most user
        for link in self.sudo():
            resp_json = link._fetch_odoo_fin('/proxy/v1/renew_token', ignore_status=True)
            link.refresh_token = resp_json.get('refresh_token', False)

    def unlink(self):
        to_unlink = self.env['account.online.link']
        for link in self:
            try:
                resp_json = link.with_context(delete_sync=True)._fetch_odoo_fin('/proxy/v1/delete_user', data={'provider_data': link.provider_data}, ignore_status=True)  # delete proxy user
                if resp_json.get('delete', True) is True:
                    to_unlink += link
            except OdooFinRedirectException:
                # Can happen that this call returns a redirect in mode link, in which case we delete the record
                to_unlink += link
                continue
            except (UserError, RedirectWarning):
                to_unlink += link
                continue
        result = super(AccountOnlineLink, to_unlink).unlink()
        self.env['account.journal']._toggle_asynchronous_fetching_cron()
        return result

    def _fetch_accounts(self, online_identifier=False):
        self.ensure_one()
        if online_identifier:
            matching_account = self.account_online_account_ids.filtered(lambda l: l.online_identifier == online_identifier)
            # Ignore account that is already there and linked to a journal as there is no need to fetch information for that one
            if matching_account and matching_account.journal_ids:
                return matching_account
            # If we have the account locally but didn't link it to a journal yet, delete it first.
            # This way, we'll get the information back from the proxy with updated balances. Avoiding potential issues.
            elif matching_account and not matching_account.journal_ids:
                matching_account.unlink()
        accounts = {}
        data = {
            'currency_code': self.company_id.currency_id.name,
        }
        swift_code = False
        while True:
            # While this is kind of a bad practice to do, it can happen that provider_data changes between
            # 2 calls, the reason is that that field contains the encrypted information needed to access the provider
            # and first call can result in an error due to the encrypted token inside provider_data being expired for example.
            # In such a case, we renew the token with the provider and send back the newly encrypted token inside provider_data
            # which result in the information having changed, henceforth why that field is passed at every loop.
            data['provider_data'] = self.provider_data
            # Retrieve information about a specific account
            if online_identifier:
                data['online_identifier'] = online_identifier

            resp_json = self._fetch_odoo_fin('/proxy/v1/accounts', data)
            for acc in resp_json.get('accounts', []):
                acc['account_online_link_id'] = self.id
                currency_id = self.env['res.currency'].with_context(active_test=False).search([('name', '=', acc.pop('currency_code', ''))], limit=1)
                if currency_id:
                    if not currency_id.active:
                        currency_id.sudo().active = True
                    acc['currency_id'] = currency_id.id
                accounts[str(acc.get('online_identifier'))] = acc
            swift_code = resp_json.get('swift_code')
            if not resp_json.get('next_data'):
                break
            data['next_data'] = resp_json.get('next_data')

        if accounts:
            self.has_unlinked_accounts = True
            return self.env['account.online.account'].create(accounts.values()), swift_code
        return False, False

    def _pre_check_fetch_transactions(self):
        self.ensure_one()
        # 'limit_time_real_cron' and 'limit_time_real' default respectively to -1 and 120.
        # Manual fallbacks applied for non-POSIX systems where this key is disabled (set to None).
        limit_time = tools.config['limit_time_real_cron'] or -1
        if limit_time <= 0:
            limit_time = tools.config['limit_time_real'] or 120
        limit_time += 20  # Add 20 seconds to be sure that the process will have been killed
        # if any account is actually creating entries and last_refresh was made less than cron_limit_time ago, skip fetching
        if (self.account_online_account_ids.filtered(lambda account: account.fetching_status == 'processing') and
                self.last_refresh + relativedelta(seconds=limit_time) > fields.Datetime.now()):
            return False
        # If not in the process of importing and auto_sync is not set, skip fetching
        if (self.env.context.get('cron') and
                not self.auto_sync and
                not self.account_online_account_ids.filtered(lambda acc: acc.fetching_status in ('planned', 'waiting', 'processing'))):
            return False
        return True

    def _fetch_transactions(self, refresh=True, accounts=False, check_duplicates=False):
        self.ensure_one()
        # return early if condition to fetch transactions are not met
        if not self._pre_check_fetch_transactions():
            return

        is_cron_running = self.env.context.get('cron')
        acc = (accounts or self.account_online_account_ids).filtered('journal_ids')
        self.last_refresh = fields.Datetime.now()
        try:
            # When manually fetching, refresh must still be done in case a redirect occurs
            # however since transactions are always fetched inside a cron, in case we are manually
            # fetching, trigger the cron and redirect customer to accounting dashboard
            accounts_to_synchronize = acc
            if not is_cron_running:
                accounts_not_to_synchronize = self.env['account.online.account']
                account_to_reauth = False
                for online_account in acc:
                    # Only get transactions on account linked to a journal
                    if refresh and online_account.fetching_status not in ('planned', 'processing'):
                        refresh_res = online_account._refresh()
                        if not refresh_res['success']:
                            if refresh_res['data'].get('mode') == 'updateCredentials':
                                account_to_reauth = online_account
                            accounts_not_to_synchronize += online_account
                            continue
                    online_account.fetching_status = 'waiting'
                if account_to_reauth:
                    return self._open_iframe(
                        mode='updateCredentials',
                        include_param={
                            'account_online_identifier': account_to_reauth.online_identifier,
                        },
                    )
                accounts_to_synchronize = acc - accounts_not_to_synchronize
                if not accounts_to_synchronize:
                    return

            def get_duplicates_from_date(statement_lines, journal):
                if check_duplicates and statement_lines:
                    from_date = fields.Date.to_string(statement_lines.sorted('date')[0].date)
                    if journal._has_duplicate_transactions(from_date):
                        return from_date

            for online_account in accounts_to_synchronize:
                journal = online_account.journal_ids[0]
                online_account.fetching_status = 'processing'
                # Committing here so that multiple thread calling this method won't execute in parallel and import duplicates transaction
                self.env.cr.commit()
                try:
                    transactions = online_account._retrieve_transactions().get('transactions', [])
                except RedirectWarning as redirect_warning:
                    self._notify_connection_update(
                        journal=journal,
                        connection_state_details={
                            'status': 'error',
                            'error_type': 'redirect_warning',
                            'error_message': redirect_warning.args[0],
                            'action': redirect_warning.args[1],
                        },
                    )
                    raise
                except OdooFinRedirectException as redirect_exception:
                    self._notify_connection_update(
                        journal=journal,
                        connection_state_details={
                            'status': 'error',
                            'error_type': 'odoofin_redirect',
                            'action': self._handle_odoofin_redirect_exception(mode=redirect_exception.mode),
                        },
                    )
                    raise

                sorted_transactions = sorted(transactions, key=lambda transaction: transaction['date'])
                if not is_cron_running:
                    # we want to import the first 100 transaction, show them to the user
                    # and import the rest asynchronously with the 'online_sync_cron_waiting_synchronization' cron
                    total = sum([transaction['amount'] for transaction in transactions])
                    statement_lines = self.env['account.bank.statement.line'].with_context(transactions_total=total)._online_sync_bank_statement(sorted_transactions[:100], online_account)
                    online_account.fetching_status = 'planned' if len(transactions) > 100 else 'done'
                    domain = None
                    if statement_lines:
                        domain = [('id', 'in', statement_lines.ids)]

                    duplicates_from_date = get_duplicates_from_date(statement_lines, journal)
                    return self.env['account.bank.statement.line']._action_open_bank_reconciliation_widget(
                        extra_domain=domain,
                        name=_('Fetched Transactions'),
                        default_context={**self.env.context, 'default_journal_id': journal.id, 'duplicates_from_date': duplicates_from_date},
                    )
                else:
                    statement_lines = self.env['account.bank.statement.line']._online_sync_bank_statement(sorted_transactions, online_account)
                    online_account.fetching_status = 'done'
                    duplicates_from_date = get_duplicates_from_date(statement_lines, journal)
                    self._notify_connection_update(
                        journal=journal,
                        connection_state_details={
                            'status': 'success',
                            'nb_fetched_transactions': len(statement_lines),
                            'action': self._show_fetched_transactions_action(statement_lines, duplicates_from_date),
                        },
                    )
            return
        except OdooFinRedirectException as e:
            return self._handle_odoofin_redirect_exception(mode=e.mode)

    def _get_consent_expiring_date(self, data=None):
        self.ensure_one()
        if not data:  # Small hack to avoid breaking the stable policy
            data = self._fetch_odoo_fin('/proxy/v1/consent_expiring_date', ignore_status=True)

        if data.get('consent_expiring_date'):
            expiring_synchronization_date = fields.Date.to_date(data['consent_expiring_date'])
            if expiring_synchronization_date != self.expiring_synchronization_date:
                # TDE TODO: master: use generic activity mixin methods instead
                bank_sync_activity_type_id = self.env.ref('account_online_synchronization.bank_sync_activity_update_consent')
                account_journal_model_id = self.env['ir.model']._get_id('account.journal')

                # Remove old activities
                self.env['mail.activity'].search([
                    ('res_id', 'in', self.journal_ids.ids),
                    ('res_model_id', '=', account_journal_model_id),
                    ('activity_type_id', '=', bank_sync_activity_type_id.id),
                    ('date_deadline', '<=', self.expiring_synchronization_date),
                    ('user_id', '=', self.env.user.id),
                ]).unlink()

                # Create a new activity for each journals for this synch
                self.expiring_synchronization_date = expiring_synchronization_date
                new_activity_vals = []
                for journal in self.journal_ids:
                    new_activity_vals.append({
                        'res_id': journal.id,
                        'res_model_id': account_journal_model_id,
                        'date_deadline': self.expiring_synchronization_date,
                        'summary': _("Bank Synchronization: Update your consent"),
                        'note': data.get('activity_message') or '',
                        'activity_type_id': bank_sync_activity_type_id.id,
                    })
                self.env['mail.activity'].create(new_activity_vals)
        elif self.expiring_synchronization_date and self.expiring_synchronization_date < fields.Date.context_today(self):
            # Avoid an infinite "expired synchro" if the provider
            # doesn't send us a new consent expiring date
            self.expiring_synchronization_date = None

    def _update_connection_status(self):
        self.ensure_one()
        resp_json = self._fetch_odoo_fin('/proxy/v2/connection_status', ignore_status=True)

        self._get_consent_expiring_date(resp_json)

        # Returning what we receive from Odoo Fin to allow function extension
        return resp_json

    def _authorize_access(self, data_access_token):
        """
        This method is used to allow an existing connection to give temporary access
        to a new connection in order to see the list of available unlinked accounts.
        We pass as parameter the list of already linked account, so that if there are
        no more accounts to link, we will receive a response telling us so and we won't
        call authorize for that connection later on.
        """
        self.ensure_one()
        data = {
            'linked_accounts': self.account_online_account_ids.filtered('journal_ids').mapped('online_identifier'),
            'record_access_token': data_access_token,
        }
        try:
            resp_json = self._fetch_odoo_fin('/proxy/v1/authorize_access', data)
            self.has_unlinked_accounts = resp_json.get('has_unlinked_accounts')
        except UserError:
            # We don't want to throw an error to the customer so ignore error
            pass

    @api.model
    def _cron_delete_unused_connection(self):
        account_online_links = self.search([
            ('write_date', '<=', fields.Datetime.now() - relativedelta(months=1)),
        ])
        for link in account_online_links:
            if not link.account_online_account_ids.filtered('journal_ids'):
                link.unlink()

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        """Override to log all message to the linked journal as well."""
        for journal in self.journal_ids:
            journal.message_post(**kwargs)
        return super(AccountOnlineLink, self).message_post(**kwargs)

    ################################
    # Callback methods from iframe #
    ################################

    def success(self, mode, data):
        if data:
            if consent_token := data.pop('manage_consent', None):
                url = self._get_odoofin_url(f'/manage-consent?consent_token={consent_token}')
                self.message_post(
                    body=_("You can manage your bank synchronization consent for this connection %s", Markup("<a href='%s' target='_blank'>%s</a>") % (url, _("here.")))
                )

            self.write(data)
            # Provider_data is extremely important and must be saved as soon as we received it
            # as it contains encrypted credentials from external provider and if we loose them we
            # loose access to the bank account, As it is possible that provider_data
            # are received during a transaction containing multiple calls to the proxy, we ensure
            # that provider_data is committed in database as soon as we received it.
            if data.get('provider_data'):
                self.env.cr.commit()

            self._update_connection_status()

        # if for some reason we just have to update the record without doing anything else, the mode will be set to 'none'
        if mode == 'none':
            return {'type': 'ir.actions.client', 'tag': 'reload'}
        try:
            method_name = '_success_%s' % mode
            method = getattr(self, method_name)
        except AttributeError:
            message = _("This version of Odoo appears to be outdated and does not support the '%s' sync mode. "
                        "Installing the latest update might solve this.", mode)
            _logger.info('Online sync: %s' % (message,))
            self.env.cr.rollback()
            self._log_information(state='error', subject=_('Internal Error'), message=message, reset_tx=True)
            raise UserError(message)
        action = method()
        return action or self.env['ir.actions.act_window']._for_xml_id('account.open_account_journal_dashboard_kanban')

    @api.model
    def connect_existing_account(self, data):
        # extract client_id and online_identifier from data and retrieve the account detail from the connection.
        # If we have a journal in context, assign to journal, otherwise create new journal then fetch transaction
        client_id = data.get('client_id')
        online_identifier = data.get('online_identifier')
        if client_id and online_identifier:
            online_link = self.search([('client_id', '=', client_id)], limit=1)
            if not online_link:
                return {'type': 'ir.actions.client', 'tag': 'reload'}
            new_account, swift_code = online_link._fetch_accounts(online_identifier=online_identifier)
            if new_account:
                new_account._assign_journal(swift_code)
                action = online_link._fetch_transactions(accounts=new_account, check_duplicates=True)
                return action or self.env['ir.actions.act_window']._for_xml_id('account.open_account_journal_dashboard_kanban')
            raise UserError(_("The consent for the selected account has expired."))
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def exchange_token(self, exchange_token):
        self.ensure_one()
        # Exchange token to retrieve client_id and refresh_token from proxy account
        data = {
            'exchange_token': exchange_token,
            'company_id': self.env.company.id,
            'user_id': self.env.user.id
        }
        resp_json = self._fetch_odoo_fin('/proxy/v1/exchange_token', data=data, ignore_status=True)
        # Write in sudo mode as those fields are protected from users
        self.sudo().write({
            'client_id': resp_json.get('client_id'),
            'refresh_token': resp_json.get('refresh_token'),
            'access_token': resp_json.get('access_token')
        })
        return True

    def _success_link(self):
        self.ensure_one()
        self._log_information(state='connected')
        account_online_accounts, swift_code = self._fetch_accounts()
        if account_online_accounts and len(account_online_accounts) == 1:
            account_online_accounts._assign_journal(swift_code)
            return self._fetch_transactions(accounts=account_online_accounts, check_duplicates=True)
        return self._link_accounts_to_journals_action(swift_code)

    def _success_updateCredentials(self):
        self.ensure_one()
        return self._fetch_transactions(refresh=False)

    def _success_refreshAccounts(self):
        self.ensure_one()
        return self._fetch_transactions(refresh=False)

    def _success_reconnect(self):
        self.ensure_one()
        self._log_information(state='connected')
        return self._fetch_transactions(check_duplicates=True)

    ##################
    # action buttons #
    ##################

    def action_new_synchronization(self, preferred_inst=None, journal_id=False):
        # Search for an existing link that was not fully connected
        online_link = self
        if not online_link or online_link.provider_type:
            online_link = self.search([('account_online_account_ids', '=', False), ('provider_type', '=', False)], limit=1)
        # If not found, create a new one
        if not online_link or online_link.provider_type:
            online_link = self.create({})
        return online_link._open_iframe('link', preferred_institution=preferred_inst, journal_id=journal_id)

    def action_update_credentials(self):
        return self._open_iframe('updateCredentials')

    def action_fetch_transactions(self):
        self.account_online_account_ids.fetching_status = None
        action = self._fetch_transactions()
        return action or self.env['ir.actions.act_window']._for_xml_id('account.open_account_journal_dashboard_kanban')

    def action_reconnect_account(self):
        return self._open_iframe('reconnect')

    def _open_iframe(self, mode='link', include_param=None, preferred_institution=False, journal_id=False):
        self.ensure_one()
        if self.client_id and self.sudo().refresh_token:
            try:
                self._get_access_token()
            except OdooFinRedirectException:
                # Delete record and open iframe in a new one
                self.unlink()
                return self.create({})._open_iframe('link')

        proxy_mode = self.env['ir.config_parameter'].sudo().get_param('account_online_synchronization.proxy_mode') or 'production'
        country = self.env['account.journal'].browse(journal_id).company_id.account_fiscal_country_id or self.env.company.country_id
        action = {
            'type': 'ir.actions.client',
            'tag': 'odoo_fin_connector',
            'id': self.id,
            'params': {
                'proxyMode': proxy_mode,
                'clientId': self.client_id,
                'accessToken': self.access_token,
                'mode': mode,
                'includeParam': {
                    'lang': get_lang(self.env).code,
                    'countryCode': country.code,
                    'countryName': country.display_name,
                    'redirect_reconnection': self.env.context.get('redirect_reconnection'),
                    'serverVersion': odoo.release.serie,
                    'mfa_type': self.env.user._mfa_type(),
                }
            },
            'context': {
                'dialog_size': 'medium',
            },
        }
        if self.provider_data:
            action['params']['providerData'] = self.provider_data
        if preferred_institution:
            action['params']['includeParam']['clickedInstitution'] = preferred_institution
        if journal_id:
            action['context']['active_model'] = 'account.journal'
            action['context']['active_id'] = journal_id

        if mode == 'link':
            user_email = self.env.user.email or self.env.ref('base.user_admin').email or ''  # Necessary for some providers onboarding
            action['params']['includeParam']['dbUuid'] = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
            action['params']['includeParam']['userEmail'] = user_email
            # Compute a hash of a random string for each connection in success
            existing_link = self.search([('state', '!=', 'disconnected'), ('has_unlinked_accounts', '=', True)])
            if existing_link:
                record_access_token = base64.b64encode(uuid.uuid4().bytes).decode('utf-8')
                for link in existing_link:
                    link._authorize_access(record_access_token)
                action['params']['includeParam']['recordAccessToken'] = record_access_token

        if include_param:
            action['params']['includeParam'].update(include_param)
        return action
