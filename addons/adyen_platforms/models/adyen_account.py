# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import uuid
from datetime import timedelta

import requests
from ast import literal_eval
from dateutil.parser import parse
from pytz import UTC
from werkzeug.urls import url_join

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.http import request
from odoo.osv import expression
from odoo.tools import format_amount, format_datetime

from odoo.addons.adyen_platforms.util import AdyenProxyAuth, to_major_currency

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
ADYEN_PAYOUT_FREQUENCIES = {
    'daily': 'DAILY',
    'weekly': 'WEEKLY',
    'biweekly': 'BIWEEKLY_ON_1ST_AND_15TH_AT_MIDNIGHT',
    'monthly': 'MONTHLY',
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
    account_code = fields.Char('Account Code')
    payout_schedule = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-weekly'),
        ('monthly', 'Monthly'),
    ], default='biweekly', required=True, string='Payout Schedule')
    next_scheduled_payout = fields.Datetime('Next Scheduled Payout', readonly=True)
    last_sync_date = fields.Datetime(default=fields.Datetime.now)

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
    account_status = fields.Selection(string='Internal Account Status', selection=[
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
        ('closed', 'Closed'),
    ], default='inactive', readonly=True)
    payout_allowed = fields.Boolean(readonly=True)

    # Status for UX
    state = fields.Selection([
        ('pending', 'Pending Validation'),  # Odoo Validation
        ('awaiting_data', 'Data To Provide'),
        ('validation', 'Data Validation'),  # KYC Validation from Adyen
        ('validated', 'Validated'),
    ], compute='_compute_state', string='Account State')

    # KYC
    adyen_kyc_ids = fields.One2many('adyen.kyc', 'adyen_account_id', string='KYC Checks', readonly=True)
    kyc_tier = fields.Integer(string='KYC Tier', default=0, readonly=True)
    kyc_status_message = fields.Html(compute='_compute_kyc_status')

    _sql_constraints = [
        ('adyen_uuid_uniq', 'UNIQUE(adyen_uuid)', 'Adyen UUID should be unique'),
    ]

    def default_get(self, fields):
        res = super().default_get(fields)
        company_fields = {
            'country_id': 'country_id',
            'state_id': 'state_id',
            'city': 'city',
            'zip': 'zip',
            'street': 'street',
            'email': 'email',
            'phone_number': 'phone',
        }

        if self.env.company.partner_id.is_company:
            company_fields.update({
                'registration_number': 'vat',
                'legal_business_name': 'name',
                'doing_business_as': 'name',
            })
            if 'is_business' in fields:
                res['is_business'] = True

        field_keys = company_fields.keys() & set(fields)
        for field_name in field_keys:
            res[field_name] = self.env.company[company_fields[field_name]]

        if not self.env.company.partner_id.is_company and {'last_name', 'first_name'} & set(fields):
            name = self.env.company.partner_id.name.split()
            res['last_name'] = name[-1]
            res['first_name'] = ' '.join(name[:-1])

        return res

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

    @api.depends('kyc_tier', 'adyen_kyc_ids', 'account_status')
    def _compute_state(self):
        for account in self:
            if account.account_status in ['inactive', 'suspended'] and account.kyc_tier == 0:
                account.state = 'pending'
            else:
                if any(k.status == 'awaiting_data' for k in account.adyen_kyc_ids):
                    account.state = 'awaiting_data'
                elif any(k.status == 'pending' for k in account.adyen_kyc_ids):
                    account.state = 'validation'
                else:
                    account.state = 'validated'

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
        adyen_account_id = super().create(values)

        # Create account on odoo.com, proxy and Adyen
        create_data = self._format_data(values)
        create_data['payoutSchedule'] = ADYEN_PAYOUT_FREQUENCIES.get(values.get('payout_schedule', 'biweekly'), 'BIWEEKLY_ON_1ST_AND_15TH_AT_MIDNIGHT'),
        response = self._adyen_rpc('v1/create_account_holder', create_data)

        adyen_account_id.with_context(update_from_adyen=True).write({
            'account_code': response['adyen_response']['accountCode'],
            'adyen_uuid': response['adyen_uuid'],
            'proxy_token': response['proxy_token'],
        })
        self.env.company.adyen_account_id = adyen_account_id.id

        return adyen_account_id

    def write(self, vals):
        adyen_fields = {
            'country_id', 'state_id', 'city', 'zip', 'street', 'house_number_or_name', 'email', 'phone_number',
            'is_business', 'legal_business_name', 'doing_business_as', 'registration_number', 'first_name',
            'last_name', 'date_of_birth', 'document_number', 'document_type',
        }
        res = super().write(vals)
        if vals.keys() & adyen_fields and not self.env.context.get('update_from_adyen'):
            self._adyen_rpc('v1/update_account_holder', self._format_data(vals))

        if 'payout_schedule' in vals:
            self._update_payout_schedule(vals['payout_schedule'])

        return res

    def unlink(self):
        self.check_access_rights('unlink')

        for adyen_account_id in self:
            adyen_account_id._adyen_rpc('v1/close_account_holder', {
                'accountHolderCode': adyen_account_id.account_holder_code,
            })
        return super().unlink()

    def _update_payout_schedule(self, payout_schedule):
        self.ensure_one()

        self._adyen_rpc('v1/update_payout_schedule', {
            'accountCode': self.account_code,
            'metadata': {
                'adyen_uuid': self.adyen_uuid,
            },
            'payoutSchedule': {
                'action': 'UPDATE',
                'schedule': ADYEN_PAYOUT_FREQUENCIES.get(payout_schedule),
            }
        })

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
        return_url = url_join(self.env.company.get_base_url(), 'adyen_platforms/create_account')
        onboarding_url = self.env['ir.config_parameter'].sudo().get_param('adyen_platforms.onboarding_url')
        return {
            'type': 'ir.actions.act_url',
            'url': url_join(onboarding_url, 'get_creation_token?return_url=%s' % return_url),
        }

    def action_show_transactions(self):
        action = self.env['ir.actions.actions']._for_xml_id('adyen_platforms.adyen_transaction_action')
        action['domain'] = expression.AND([[('adyen_account_id', '=', self.id)], literal_eval(action.get('domain', '[]'))])
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
        fields = values.keys()
        data = {
            'accountHolderCode': values.get('account_holder_code') or self.account_holder_code,
        }
        holder_details = {}

        # *ALL* the address fields are required if one of them changes
        address_fields = {'country_id', 'state_id', 'city', 'zip', 'street', 'house_number_or_name'}
        if address_fields & fields:
            country_id = self.env['res.country'].browse(values.get('country_id')) if values.get('country_id') else self.country_id
            state_id = self.env['res.country.state'].browse(values.get('state_id')) if values.get('state_id') else self.state_id
            holder_details['address'] = {
                'country': country_id.code,
                'stateOrProvince': state_id.code or None,
                'city': values.get('city') or self.city,
                'postalCode': values.get('zip') or self.zip,
                'street': values.get('street') or self.street,
                'houseNumberOrName': values.get('house_number_or_name') or self.house_number_or_name,
            }

        if 'email' in values:
            holder_details['email'] = values['email']

        if 'phone_number' in values:
            holder_details['fullPhoneNumber'] = values['phone_number']

        if 'is_business' in values:
            data['legalEntity'] = 'Business' if values['is_business'] else 'Individual'

        if (values.get('is_business') or self.is_business) and {'legal_business_name', 'doing_business_as', 'registration_number'} & fields:
            business_details = holder_details['business_details'] = {}
            for source, dest in [
                ('legal_business_name', 'legalBusinessName'),
                ('doing_business_as', 'doingBusinessAs'),
                ('registration_number', 'registrationNumber'),
            ]:
                if source in values:
                    business_details[dest] = values[source]

        elif {'first_name', 'last_name', 'date_of_birth', 'document_number', 'document_type'} & fields:
            holder_details['individualDetails'] = {}

            if {'first_name', 'last_name'} & fields:
                holder_details['individualDetails']['name'] = {
                    'firstName': values.get('first_name') or self.first_name,
                    'lastName': values.get('last_name') or self.last_name
                }

            if 'date_of_birth' in fields:
                holder_details['individualDetails'].setdefault('personalData', {})['dateOfBirth'] = str(values['date_of_birth'])

            document_number = values.get('document_number') or self.document_number
            if self.document_number and 'document_number' in fields:
                holder_details['individualDetails'].setdefault('personalData', {})['documentData'] = [{
                    'number': document_number,
                    'type': values.get('document_type') or self.document_type,
                }]

        if holder_details:
            data['accountHolderDetails'] = holder_details

        return data

    def _adyen_rpc(self, operation, adyen_data=None):
        adyen_data = adyen_data or {}
        if operation == 'v1/create_account_holder':
            url = self.env['ir.config_parameter'].sudo().get_param('adyen_platforms.onboarding_url')
            params = {
                'creation_token': request.session.get('adyen_creation_token'),
                'base_url': self.get_base_url(),
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
            raise UserError(_('A timeout occurred while trying to reach the Adyen proxy.'))
        except Exception:
            raise UserError(_('The Adyen proxy is not reachable, please try again later.'))
        response = req.json()

        if 'error' in response:
            name = response['error']['data'].get('name').rpartition('.')[-1]
            if name == 'ValidationError':
                raise ValidationError(response['error']['data'].get('arguments')[0])
            else:
                _logger.warning('Proxy error: %s', response['error'])
                raise UserError(
                    _("We had troubles reaching Adyen, please retry later or contact the support if the problem persists"))
        return response.get('result')

    @api.model
    def _sync_adyen_cron(self):
        self.env['adyen.account'].search([]).sync_transactions()

    def _handle_notification(self, notification_data):
        self.ensure_one()

        content = notification_data.get('content', {})
        event_type = notification_data.get('eventType')

        if event_type == 'ODOO_ACCOUNT_STATUS_CHANGE':
            self._handle_odoo_account_status_change(content)
        elif event_type == 'ACCOUNT_HOLDER_STATUS_CHANGE':
            self._handle_account_holder_status_change_notification(content)
        elif event_type == 'ACCOUNT_HOLDER_VERIFICATION':
            self._handle_account_holder_verification_notification(content)
        elif event_type == 'ACCOUNT_UPDATED':
            self._handle_account_updated_notification(content)
        elif event_type == 'ACCOUNT_HOLDER_PAYOUT':
            self._handle_account_holder_payout(content)
        else:
            _logger.warning(_("Unknown eventType received: %s", event_type))

    def _handle_odoo_account_status_change(self, content):
        self.ensure_one()

        new_status = content.get('newStatus')
        if new_status == 'active' and self.account_status in ['suspended', 'inactive']:
            self._adyen_rpc('v1/unsuspend_account_holder', {
                'accountHolderCode': self.account_holder_code,
            })
        elif new_status == 'rejected':
            self._adyen_rpc('v1/close_account_holder', {
                'accountHolderCode': self.account_holder_code,
            })

    def _handle_account_holder_status_change_notification(self, content):
        self.ensure_one()

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

    def _handle_account_holder_verification_notification(self, content):
        self.ensure_one()

        status = ADYEN_VALIDATION_MAP.get(content.get('verificationStatus'))
        document = '_'.join(content.get('verificationType', '').lower().split('_')[:-1])  # bank_account, identity, passport, etc.
        status_message = content.get('statusSummary', {}).get('kycCheckDescription')

        bank_uuid = content.get('bankAccountUUID')
        shareholder_uuid = content.get('shareholderCode')

        kyc = self.adyen_kyc_ids.filtered(lambda k: k.verification_type == document)
        if bank_uuid:
            kyc = kyc.filtered(lambda k: k.bank_account_id.bank_account_uuid == bank_uuid or not k.bank_account_id)
        elif shareholder_uuid:
            kyc = kyc.filtered(lambda k: k.shareholder_id.shareholder_uuid == shareholder_uuid or not k.shareholder_id)
        else:
            kyc = kyc.filtered(lambda k: not k.shareholder_id and not k.bank_account_id)

        if not kyc:
            additional_data = {}
            if document == 'bank_account' and bank_uuid:
                bank_account_id = self.env['adyen.bank.account'].sudo().search([('bank_account_uuid', '=', bank_uuid)])
                additional_data['bank_account_id'] = bank_account_id.id
            if shareholder_uuid:
                shareholder_id = self.env['adyen.shareholder'].sudo().search([('shareholder_uuid', '=', shareholder_uuid)])
                additional_data['shareholder_id'] = shareholder_id.id

            self.env['adyen.kyc'].sudo().create({
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

    def _handle_account_updated_notification(self, content):
        self.ensure_one()
        scheduled_date = content.get('payoutSchedule', {}).get('nextScheduledPayout')
        if scheduled_date:
            self.next_scheduled_payout = parse(scheduled_date).astimezone(UTC).replace(tzinfo=None)

    def _handle_account_holder_payout(self, content):
        self.ensure_one()
        status = content.get('status', {}).get('statusCode')

        if status == 'Failed':
            status_message = _('Failed payout: %s', content['status']['message']['text'])
            self.sudo().message_post(body=status_message, subtype_xmlid="mail.mt_comment")

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
                    if not max_create_date:
                        max_create_date = create_date
                    if create_date <= account.last_sync_date:
                        next_page = False
                        break

                    status = transaction.get('transactionStatus')
                    if status in ['Payout', 'PayoutReversed']:
                        reference = transaction.get('pspReference') or transaction.get('disputePspReference')
                        tx_sudo = account.transaction_payout_ids.sudo().filtered(lambda t: t.reference == reference)
                        if not tx_sudo:
                            self.env['adyen.transaction.payout'].sudo()._create_missing_payout(account.id, transaction)
                        else:
                            tx_sudo.status = status
                    else:
                        if status in ['Chargeback', 'ChargebackReceived']:
                            transaction['pspReference'] = transaction.get('disputePspReference')
                        tx_sudo, _reference, _capture_reference = account.transaction_ids.sudo()._get_tx_from_notification(transaction)
                        if not tx_sudo:
                            tx_sudo = self.env['adyen.transaction'].sudo()._create_missing_tx(account.id, transaction)
                        tx_sudo._update_status(status, create_date)
                        updated_transactions |= tx_sudo
                account.last_sync_date = max_create_date
        updated_transactions.sudo()._post_transaction_sync()

    def _fetch_transactions(self, page=1):
        self.ensure_one()
        response = self._adyen_rpc('v1/get_transactions', {
            'accountHolderCode': self.account_holder_code,
            'transactionListsPerAccount': [{
                'accountCode': self.account_code,
                'page': page,
            }]
        })
        transaction_list = response['accountTransactionLists'][0]
        return transaction_list['transactions'], transaction_list['hasNextPage']


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
        if not self.user_has_groups('base.group_erp_manager'):
            raise AccessError(_("You can't access account balance."))

        if not self.env.company.adyen_account_id:
            return {}

        balance_fields = {'balance': 'balance', 'onHoldBalance': 'on_hold', 'pendingBalance': 'pending'}
        balances = self.env['adyen.account.balance'].sudo().search([
            ('adyen_account_id', '=', self.env.company.adyen_account_id.id)
        ])

        delta = fields.Datetime.now() - timedelta(hours=1)
        if not balances or any(b.write_date <= delta for b in balances):
            response = {}
            try:
                response = self.env.company.adyen_account_id._adyen_rpc('v1/account_holder_balance', {
                    'accountHolderCode': self.env.company.adyen_account_id.account_holder_code,
                })
            except UserError as e:
                _logger.warning(_('Cannot update account balance, showing previous values: %s', e))

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
                    bal[balance_fields.get(total_balance)] = to_major_currency(balance.get('value', 0), currency_id.decimal_places)

        warning_delta = fields.Datetime.now() - timedelta(hours=2)
        return [{
            'currency': b.currency_id.name,
            'balance': format_amount(self.env, b.balance, b.currency_id),
            'payout_date': format_datetime(self.env, self.env.company.adyen_account_id.next_scheduled_payout, dt_format='short'),
            'last_update_warning': b.write_date <= warning_delta,
            'last_update': format_datetime(self.env, b.write_date),
        } for b in balances]
