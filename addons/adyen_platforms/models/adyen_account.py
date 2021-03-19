# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import requests
import uuid

from datetime import timedelta
from dateutil.parser import parse
from werkzeug.urls import url_join
from pytz import UTC

from odoo import api, fields, models, _
from odoo.http import request
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import format_amount, format_date, format_datetime, date_utils
from odoo.tools.safe_eval import safe_eval

from odoo.addons.adyen_platforms.util import AdyenProxyAuth

_logger = logging.getLogger(__name__)

TIMEOUT = 60

ADYEN_STATUS_MAP = {
    'Active': 'active',
    'Inactive': 'inactive',
    'Suspended': 'suspended',
    'Closed': 'closed',
}
ADYEN_VALIDATION_MAP = {
    'FAILED': 'failed',
    'INVALID_DATA': 'awaiting_data',
    'RETRY_LIMIT_REACHED': 'awaiting_data',
    'AWAITING_DATA': 'awaiting_data',
    'DATA_PROVIDED': 'data_provided',
    'PENDING': 'pending',
    'PASSED': 'passed',
}


class AdyenAccount(models.Model):
    _name = 'adyen.account'
    _inherit = ['mail.thread', 'adyen.id.mixin', 'adyen.address.mixin']

    _description = 'Adyen for Platforms Account'
    _rec_name = 'full_name'

    # Credentials
    proxy_token = fields.Char('Proxy Token')
    adyen_uuid = fields.Char('Adyen UUID')
    account_holder_code = fields.Char('Account Holder Code', default=lambda self: uuid.uuid4().hex)

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    shareholder_ids = fields.One2many('adyen.shareholder', 'adyen_account_id', string='Shareholders')
    bank_account_ids = fields.One2many('adyen.bank.account', 'adyen_account_id', string='Bank Accounts')
    transaction_ids = fields.One2many('adyen.transaction', 'adyen_account_id', string='Transactions')
    transactions_count = fields.Integer(compute='_compute_transactions_count')
    transaction_payout_ids = fields.One2many('adyen.transaction.payout', 'adyen_account_id')

    is_business = fields.Boolean('Is a business', required=True)

    # Payout
    account_code = fields.Char('Account Code') # Used for payout
    payout_schedule = fields.Selection([
        ('day', 'Daily'),
        ('week', 'Weekly'),
        ('month', 'Monthly'),
    ], default='week', required=True, string='Payout Schedule')
    next_scheduled_payout = fields.Date('Next Scheduled Payout', compute='_compute_next_scheduled_payout', store=True)
    last_sync_date = fields.Datetime()

    # Contact Info
    full_name = fields.Char(compute='_compute_full_name')
    email = fields.Char('Email', required=True)
    phone_number = fields.Char('Phone Number', required=True)

    # Individual
    first_name = fields.Char('First Name')
    last_name = fields.Char('Last Name')
    date_of_birth = fields.Date('Date of birth')
    document_number = fields.Char('ID Number',
                                  help="The type of ID Number required depends on the country:\n"
                                  "US: Social Security Number (9 digits or last 4 digits)\n"
                                  "Canada: Social Insurance Number\nItaly: Codice fiscale\n"
                                  "Australia: Document Number")
    document_type = fields.Selection(string='Document Type', selection=[
        ('ID', 'ID'),
        ('PASSPORT', 'Passport'),
        ('VISA', 'Visa'),
        ('DRIVINGLICENSE', 'Driving license'),
    ], default='ID')

    # Business
    legal_business_name = fields.Char('Legal Business Name')
    doing_business_as = fields.Char('Doing Business As')
    registration_number = fields.Char('Registration Number')

    # Adyen Account Status - internal use
    account_status = fields.Selection(string='Account Status', selection=[
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
        ('closed', 'Closed'),
    ], default='inactive', readonly=True)
    payout_allowed = fields.Boolean(readonly=True)

    # KYC
    adyen_kyc_ids = fields.One2many('adyen.kyc', 'adyen_account_id', string='KYC Checks', readonly=True)
    kyc_tier = fields.Integer(string='KYC Tier', default=0, readonly=True)
    kyc_status_message = fields.Html(compute='_compute_kyc_status')

    _sql_constraints = [
        ('adyen_uuid_uniq', 'UNIQUE(adyen_uuid)', 'Adyen UUID should be unique'),
    ]

    @api.depends('transaction_ids')
    def _compute_transactions_count(self):
        for adyen_account_id in self:
            adyen_account_id.transactions_count = len(adyen_account_id.transaction_ids)

    @api.depends('first_name', 'last_name', 'legal_business_name')
    def _compute_full_name(self):
        for adyen_account_id in self:
            if adyen_account_id.is_business:
                adyen_account_id.full_name = adyen_account_id.legal_business_name
            else:
                adyen_account_id.full_name = "%s %s" % (adyen_account_id.first_name, adyen_account_id.last_name)

    @api.depends('payout_schedule')
    def _compute_next_scheduled_payout(self):
        today = fields.Date.today()
        for account in self:
            account.next_scheduled_payout = date_utils.end_of(today, account.payout_schedule)

    @api.depends_context('lang')
    @api.depends('adyen_kyc_ids')
    def _compute_kyc_status(self):
        self.kyc_status_message = False
        doc_types = dict(self.env['adyen.kyc']._fields['verification_type']._description_selection(self.env))
        for account in self.filtered('adyen_kyc_ids.status_message'):
            checks = {}
            for kyc in account.adyen_kyc_ids.filtered('status_message'):
                doc_type = doc_types.get(kyc.verification_type, _('Other'))
                checks.setdefault(doc_type, []).append({
                    'document': kyc.document,
                    'message': kyc.status_message,
                })

            account.kyc_status_message = self.env['ir.qweb']._render('adyen_platforms.kyc_status_message', {
                'checks': checks
            })

    @api.model
    def create(self, values):
        # Create account on odoo.com, proxy and Adyen
        response = self._adyen_rpc('v1/create_account_holder', self._format_data(values))

        values['account_code'] = response['adyen_response']['accountCode']
        values['adyen_uuid'] = response['adyen_uuid']
        values['proxy_token'] = response['proxy_token']

        adyen_account_id = super(AdyenAccount, self).create(values)
        self.env.company.adyen_account_id = adyen_account_id.id

        return adyen_account_id

    def write(self, vals):
        adyen_fields = {
            'country_id', 'state_id', 'city', 'zip', 'street', 'house_number_or_name', 'email', 'phone_number',
            'is_business', 'legal_business_name', 'doing_business_as', 'registration_number', 'first_name',
            'last_name', 'date_of_birth', 'document_number', 'document_type',
        }
        if set(vals.keys()) & adyen_fields and not self.env.context.get('update_from_adyen'):
            self._adyen_rpc('v1/update_account_holder', self._format_data(vals))

        return super(AdyenAccount, self).write(vals)

    def unlink(self):
        for adyen_account_id in self:
            adyen_account_id._adyen_rpc('v1/close_account_holder', {
                'accountHolderCode': adyen_account_id.account_holder_code,
            })
        return super(AdyenAccount, self).unlink()

    @api.model
    def action_create_redirect(self):
        '''
        Accessing the FormView to create an Adyen account needs to be done through this action.
        The action will redirect the user to accounts.odoo.com to link an Odoo user_id to the Adyen
        account. After logging in on odoo.com the user will be redirected to his DB with a token in
        the URL. This token is then needed to create the Adyen account.
        '''
        if self.env.company.adyen_account_id:
            # An account already exists, show it
            return {
                'name': _('Adyen Account'),
                'view_mode': 'form',
                'res_model': 'adyen.account',
                'res_id': self.env.company.adyen_account_id.id,
                'type': 'ir.actions.act_window',
            }
        return_url = url_join(self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url'), 'adyen_platforms/create_account')
        onboarding_url = self.env['ir.config_parameter'].sudo().get_param('adyen_platforms.onboarding_url')
        return {
            'type': 'ir.actions.act_url',
            'url': url_join(onboarding_url, 'get_creation_token?return_url=%s' % return_url),
        }

    def action_show_transactions(self):
        action = self.env['ir.actions.actions']._for_xml_id('adyen_platforms.adyen_transaction_action')
        action['domain'] = expression.AND([[('adyen_account_id', '=', self.id)], safe_eval(action.get('domain', '[]'))])
        return action

    def _upload_photo_id(self, document_type, content, filename):
        test_mode = self.env['ir.config_parameter'].sudo().get_param('adyen_platforms.test_mode')
        self._adyen_rpc('v1/upload_document', {
            'documentDetail': {
                'accountHolderCode': self.account_holder_code,
                'documentType': document_type,
                'filename': filename,
                'description': 'PASSED' if test_mode else '',
            },
            'documentContent': content.decode(),
        })

    def _format_data(self, values):
        fields = set(values.keys())
        data = {
            'accountHolderCode': values.get('account_holder_code') or self.account_holder_code,
        }

        # *ALL* the address fields are required if one of them changes
        address_fields = {'country_id', 'state_id', 'city', 'zip', 'street', 'house_number_or_name'}
        if address_fields & fields:
            data.setdefault('accountHolderDetails', {})
            country_id = self.env['res.country'].browse(values.get('country_id')) if values.get('country_id') else self.country_id
            state_id = self.env['res.country.state'].browse(values.get('state_id')) if values.get('state_id') else self.state_id
            data['accountHolderDetails']['address'] = {
                'country': country_id.code,
                'stateOrProvince': state_id.code or None,
                'city': values.get('city') or self.city,
                'postalCode': values.get('zip') or self.zip,
                'street': values.get('street') or self.street,
                'houseNumberOrName': values.get('house_number_or_name') or self.house_number_or_name,
            }

        if 'email' in fields:
            data.setdefault('accountHolderDetails', {}).update({'email': values.get('email')})

        if 'phone_number' in fields:
            data.setdefault('accountHolderDetails', {}).update({'fullPhoneNumber': values.get('phone_number')})

        if 'is_business' in fields:
            data['legalEntity'] = 'Business' if values.get('is_business') else 'Individual'

        if (values.get('is_business') or self.is_business) and {'legal_business_name', 'doing_business_as', 'registration_number'} & fields:
            data.setdefault('accountHolderDetails', {}).setdefault('businessDetails', {})
            if 'legal_business_name' in fields:
                data['accountHolderDetails']['businessDetails']['legalBusinessName'] = values.get('legal_business_name')

            if 'doing_business_as' in fields:
                data['accountHolderDetails']['businessDetails']['doingBusinessAs'] = values.get('doing_business_as')

            if 'registration_number' in fields:
                data['accountHolderDetails']['businessDetails']['registrationNumber'] = values.get('registration_number')

        elif {'first_name', 'last_name', 'date_of_birth', 'document_number', 'document_type'} & fields:
            data.setdefault('accountHolderDetails', {}).setdefault('individualDetails', {})

            if {'first_name', 'last_name'} & fields:
                data['accountHolderDetails']['individualDetails'].setdefault('name', {}).update({
                    'firstName': values.get('first_name') or self.first_name,
                    'lastName': values.get('last_name') or self.last_name
                })

            if 'date_of_birth' in fields:
                data['accountHolderDetails']['individualDetails'].setdefault('personalData', {}).update({'dateOfBirth': str(values.get('date_of_birth'))})

            document_number = values.get('document_number') or self.document_number
            if self.document_number and 'document_number' in fields:
                data['accountHolderDetails']['individualDetails'].setdefault('personalData', {}).update({'documentData': [{
                    'number': document_number,
                    'type': values.get('document_type') or self.document_type,
                }]})

        return data

    def _adyen_rpc(self, operation, adyen_data={}):
        if operation == 'v1/create_account_holder':
            url = self.env['ir.config_parameter'].sudo().get_param('adyen_platforms.onboarding_url')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            params = {
                'creation_token': request.session.get('adyen_creation_token'),
                'base_url': base_url,
                'adyen_data': adyen_data,
            }
            auth = None
        else:
            url = self.env['ir.config_parameter'].sudo().get_param('adyen_platforms.proxy_url')
            params = {
                'adyen_uuid': self.adyen_uuid,
                'adyen_data': adyen_data,
            }
            auth = AdyenProxyAuth(self)

        payload = {
            'jsonrpc': '2.0',
            'params': params,
        }
        try:
            req = requests.post(url_join(url, operation), json=payload, auth=auth, timeout=TIMEOUT)
            req.raise_for_status()
        except requests.exceptions.Timeout:
            raise UserError(_('A timeout occured while trying to reach the Adyen proxy.'))
        except Exception:
            raise UserError(_('The Adyen proxy is not reachable, please try again later.'))
        response = req.json()

        if 'error' in response:
            name = response['error']['data'].get('name').rpartition('.')[-1]
            if name == 'ValidationError':
                raise ValidationError(response['error']['data'].get('arguments')[0])
            else:
                raise UserError(
                    _("We had troubles reaching Adyen, please retry later or contact the support if the problem persists"))
        return response.get('result')

    @api.model
    def _sync_adyen_cron(self):
        self._process_payouts()
        self.env['adyen.account'].search([]).sync_transactions()

    @api.model
    def _process_payouts(self):
        for adyen_payout_id in self.search([('next_scheduled_payout', '<=', fields.Date.today())]):
            adyen_payout_id.send_payout_request(notify=False)
            adyen_payout_id._compute_next_scheduled_payout()

    def _handle_notification(self, notification_data):
        self.ensure_one()

        content = notification_data.get('content', {})
        event_type = notification_data.get('eventType')

        self._handle_invalid_fields(content)

        # TODO Move all that crap to a method on adyen.account
        if event_type == 'ODOO_ACCOUNT_STATUS_CHANGE':
            # Notification coming from odoo.com
            # Do not update the adyen.account status here, it will be done through a notification from Adyen.
            new_status = content.get('newStatus')

            if new_status == 'active' and self.account_status in ['suspended', 'inactive']:
                self._adyen_rpc('v1/unsuspend_account_holder', {
                    'accountHolderCode': self.account_holder_code,
                })
            elif new_status == 'rejected':
                self._adyen_rpc('v1/close_account_holder', {
                    'accountHolderCode': self.account_holder_code,
                })
                # TODO log a note, send an email or something?
            # Regular notification from Adyen
        elif event_type == 'ACCOUNT_HOLDER_STATUS_CHANGE':
            # Account Status
            new_status = ADYEN_STATUS_MAP.get(content.get('newStatus', {}).get('status'))
            if new_status and new_status != self.account_status:
                self.account_status = new_status

            # Tier
            tier = content.get('newStatus', {}).get('processingState', {}).get('tierNumber', None)
            if isinstance(tier, int) and tier != self.kyc_tier:
                self.kyc_tier = tier

            # Payout
            payout_allowed = content.get('newStatus', {}).get('payoutState', {}).get('allowPayout', None)
            if payout_allowed is not None:
                self.payout_allowed = payout_allowed == 'true'

            # Events
            events = content.get('newStatus', {}).get('events')
            if events:
                reasons = []
                for event in events:
                    account_event = event.get('AccountEvent', {}).get('reason')
                    if account_event:
                        reasons.append(account_event)

                status_message = self.env['ir.qweb']._render('adyen_platforms.status_message', {
                    'message': content.get('reason'),
                    'reasons': reasons,
                })
                self.sudo().message_post(body=status_message, subtype_xmlid="mail.mt_comment")
        elif event_type == 'ACCOUNT_HOLDER_VERIFICATION':
            status = ADYEN_VALIDATION_MAP.get(content.get('verificationStatus'))
            document = '_'.join(content.get('verificationType', '').lower().split('_')[:-1])  # bank_account, identity, passport, etc.
            status_message = content.get('statusSummary', {}).get('kycCheckDescription')

            bank_uuid = content.get('bankAccountUUID')
            shareholder_uuid = content.get('shareholderCode')

            kyc = self.env['adyen.kyc']
            if bank_uuid:
                kyc = self.adyen_kyc_ids.filtered(lambda k: k.verification_type == document and (k.bank_account_id.bank_account_uuid == bank_uuid or not k.bank_account_id))
            elif shareholder_uuid:
                kyc = self.adyen_kyc_ids.filtered(lambda k: k.verification_type == document and (k.shareholder_id.shareholder_uuid == shareholder_uuid or not k.shareholder_id))
            else:
                kyc = self.adyen_kyc_ids.filtered(lambda k: k.verification_type == document and not k.shareholder_id and not k.bank_account_id)

            if not kyc:
                additional_data = {}
                if document == 'bank_account' and bank_uuid:
                    bank_account_id = self.env['adyen.bank.account'].sudo().search([('bank_account_uuid', '=', bank_uuid)])
                    additional_data['bank_account_id'] = bank_account_id.id
                if shareholder_uuid:
                    shareholder_id = self.env['adyen.shareholder'].sudo().search([('shareholder_uuid', '=', shareholder_uuid)])
                    additional_data['shareholder_id'] = shareholder_id.id

                kyc = self.env['adyen.kyc'].sudo().create({
                    'verification_type': document,
                    'adyen_account_id': self.id,
                    'status': status,
                    'status_message': status_message,
                    'last_update': fields.Datetime.now(),
                    **additional_data
                })
            else:
                if bank_uuid and not kyc.bank_account_id:
                    bank_account_id = self.env['adyen.bank.account'].sudo().search([('bank_account_uuid', '=', bank_uuid)])
                    kyc.bank_account_id = bank_account_id.id
                if shareholder_uuid and not kyc.shareholder_id:
                    shareholder_id = self.env['adyen.shareholder'].sudo().search([('shareholder_uuid', '=', shareholder_uuid)])
                    kyc.shareholder_id = shareholder_id.id

                if status != kyc.status:
                    kyc.write({
                        'status': status,
                        'status_message': status_message,
                        'last_update': fields.Datetime.now(),
                    })

    # TODO parse invalidFields
    def _handle_invalid_fields(self, content):
        pass
        # if content.get('invalidFields'):
        #     msg = ''
        #     for error in content['invalidFields']:
        #         msg += '%s\n' % error['ErrorFieldType'].get('errorDescription')
        #     self.kyc_status_message = msg
        #     self.message_post(body=self.kyc_status_message, subtype_xmlid="mail.mt_comment")

    def sync_transactions(self):
        updated_transactions = self.env['adyen.transaction']
        for account in self:
            page = 1
            next_page = True
            max_create_date = False

            while next_page:
                transactions, next_page = account._fetch_transactions(page)
                page += 1

                for transaction in transactions:
                    create_date = parse(transaction.get('creationDate')).astimezone(UTC).replace(tzinfo=None)
                    # TODO improve shenanigan
                    if not max_create_date:
                        max_create_date = create_date
                    if account.last_sync_date and create_date <= account.last_sync_date:
                        next_page = False
                        break

                    reference = transaction.get('pspReference', transaction.get('disputePspReference'))
                    status = transaction.get('transactionStatus')

                    # TODO handle chargeback
                    if status in ['Payout', 'PayoutReversed']:
                        tx_sudo = account.transaction_payout_ids.sudo().filtered(lambda t: t.reference == reference)
                        if not tx_sudo:
                            tx_sudo = self.env['adyen.transaction.payout'].sudo()._create_missing_payout(account.id, transaction)
                        else:
                            tx_sudo.status = status
                    else:
                        if status in ['Chargeback']:
                            transaction['pspReference'] = transaction.get('disputePspReference')
                        tx_sudo = account.transaction_ids.sudo().filtered(lambda t: t.reference == reference)
                        if not tx_sudo:
                            tx_sudo = self.env['adyen.transaction'].sudo()._create_missing_tx(account.id, transaction)
                        tx_sudo._update_status(status, create_date)
                        updated_transactions |= tx_sudo
                account.last_sync_date = max_create_date
        updated_transactions.sudo()._post_transaction_sync()

    def _fetch_transactions(self, page=1):
        response = self._adyen_rpc('v1/get_transactions', {
            'accountHolderCode': self.account_holder_code,
            'transactionListsPerAccount': [{
                'accountCode': self.account_code,
                'page': page,
            }]
        })
        transaction_list = response['accountTransactionLists'][0]
        return transaction_list['transactions'], transaction_list['hasNextPage']

    def send_payout_request(self, notify=True):
        response = self._adyen_rpc('v1/account_holder_balance', {
            'accountHolderCode': self.account_holder_code,
        })
        balances = next(account_balance['detailBalance']['balance'] for account_balance in response['balancePerAccount'] if account_balance['accountCode'] == self.account_code)
        if notify and not balances:
            self.env['bus.bus'].sendone(
                (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
                {'type': 'simple_notification', 'title': _('No pending balance'), 'message': _('No balance is currently awaiting payout.')}
            )
        for balance in balances:
            response = self._adyen_rpc('v1/payout_request', {
                'accountCode': self.account_code,
                'accountHolderCode': self.account_holder_code,
                'amount': balance,
            })
            if notify and response['resultCode'] == 'Received':
                currency_id = self.env['res.currency'].search([('name', '=', balance['currency'])])
                value = round(balance['value'] / (10 ** currency_id.decimal_places), 2) # Convert from minor units
                amount = str(value) + currency_id.symbol if currency_id.position == 'after' else currency_id.symbol + str(value)
                message = _('Successfully sent payout request for %s', amount)
                self.env['bus.bus'].sendone(
                    (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
                    {'type': 'simple_notification', 'title': _('Payout Request sent'), 'message': message}
                )

class AdyenAccountBalance(models.Model):
    _name = 'adyen.account.balance'
    _description = 'Adyen Account Balance'

    adyen_account_id = fields.Many2one('adyen.account', required=True, ondelete='cascade')
    currency_id = fields.Many2one('res.currency')
    balance = fields.Float(default=0.0)
    on_hold = fields.Float(default=0.0)
    pending = fields.Float(default=0.0)

    @api.model
    def get_account_balance(self):
        if not self.env.company.adyen_account_id:
            return {}

        balance_fields = {'balance': 'balance', 'onHoldBalance': 'on_hold', 'pendingBalance': 'pending'}
        balances = self.env['adyen.account.balance'].sudo().search([
            ('adyen_account_id', '=', self.env.company.adyen_account_id.id)
        ])

        delta = fields.Datetime.now() - timedelta(minutes=1)  # TODO change to 1 hour before merge
        if not balances or any(b.write_date <= delta for b in balances):
            response = {}
            try:
                response = self.env.company.adyen_account_id._adyen_rpc('v1/account_holder_balance', {
                    'accountHolderCode': self.env.company.adyen_account_id.account_holder_code,
                })
            except UserError as e:
                logging.warning(_('Cannot update account balance, showing previous values: %s', e))

            balances.write({
                f: 0 for f in balance_fields.values()
            })
            for total_balance, adyen_balances in response.get('totalBalance', {}).items():
                for balance in adyen_balances:
                    currency_id = self.env['res.currency'].search([('name', '=', balance.get('currency'))])
                    bal = balances.filtered(lambda b: b.currency_id == currency_id)
                    if not bal:
                        bal = self.env['adyen.account.balance'].sudo().create({
                            'adyen_account_id': self.env.company.adyen_account_id.id,
                            'currency_id': currency_id.id,
                        })
                        balances |= bal
                    bal[balance_fields.get(total_balance)] = balance.get('value', 0) / (10 ** 2)

        warning_delta = fields.Datetime.now() - timedelta(hours=2)
        return [{
            'currency': b.currency_id.name,
            'balance': format_amount(self.env, b.balance, b.currency_id),
            'payout_date': format_date(self.env, self.env.company.adyen_account_id.next_scheduled_payout),
            'last_update_warning': b.write_date <= warning_delta,
            'last_update': format_datetime(self.env, b.write_date),
        } for b in balances]
