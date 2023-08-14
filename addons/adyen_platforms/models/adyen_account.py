# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os
import requests
import uuid
from werkzeug.urls import url_join

from odoo import api, fields, models, _
from odoo.http import request
from odoo.exceptions import UserError, ValidationError
from odoo.tools import date_utils

from odoo.addons.adyen_platforms.util import AdyenProxyAuth

ADYEN_AVAILABLE_COUNTRIES = ['US', 'AT', 'AU', 'BE', 'CA', 'CH', 'CZ', 'DE', 'ES', 'FI', 'FR', 'GB', 'GR', 'HR', 'IE', 'IT', 'LT', 'LU', 'NL', 'PL', 'PT']
TIMEOUT = 60


class AdyenAddressMixin(models.AbstractModel):
    _name = 'adyen.address.mixin'
    _description = 'Adyen for Platforms Address Mixin'

    country_id = fields.Many2one('res.country', string='Country', domain=[('code', 'in', ADYEN_AVAILABLE_COUNTRIES)], required=True)
    country_code = fields.Char(related='country_id.code')
    state_id = fields.Many2one('res.country.state', string='State', domain="[('country_id', '=?', country_id)]")
    state_code = fields.Char(related='state_id.code')
    city = fields.Char('City', required=True)
    zip = fields.Char('ZIP', required=True)
    street = fields.Char('Street', required=True)
    house_number_or_name = fields.Char('House Number Or Name', required=True)


class AdyenIDMixin(models.AbstractModel):
    _name = 'adyen.id.mixin'
    _description = 'Adyen for Platforms ID Mixin'

    id_type = fields.Selection(string='Photo ID type', selection=[
        ('PASSPORT', 'Passport'),
        ('ID_CARD', 'ID Card'),
        ('DRIVING_LICENSE', 'Driving License'),
    ])
    id_front = fields.Binary('Photo ID Front', help="Allowed formats: jpg, pdf, png. Maximum allowed size: 4MB.")
    id_front_filename = fields.Char()
    id_back = fields.Binary('Photo ID Back', help="Allowed formats: jpg, pdf, png. Maximum allowed size: 4MB.")
    id_back_filename = fields.Char()

    def write(self, vals):
        res = super(AdyenIDMixin, self).write(vals)

        # Check file formats
        if vals.get('id_front'):
            self._check_file_requirements(vals.get('id_front'), vals.get('id_front_filename'))
        if vals.get('id_back'):
            self._check_file_requirements(vals.get('id_back'), vals.get('id_back_filename'))

        for adyen_account in self:
            if vals.get('id_front'):
                document_type = adyen_account.id_type
                if adyen_account.id_type in ['ID_CARD', 'DRIVING_LICENSE']:
                    document_type += '_FRONT'
                adyen_account._upload_photo_id(document_type, adyen_account.id_front, adyen_account.id_front_filename)
            if vals.get('id_back') and adyen_account.id_type in ['ID_CARD', 'DRIVING_LICENSE']:
                document_type = adyen_account.id_type + '_BACK'
                adyen_account._upload_photo_id(document_type, adyen_account.id_back, adyen_account.id_back_filename)
            return res

    @api.model
    def _check_file_requirements(self, content, filename):
        file_extension = os.path.splitext(filename)[1]
        file_size = int(len(content) * 3/4) # Compute file_size in bytes
        if file_extension not in ['.jpeg', '.jpg', '.pdf', '.png']:
            raise ValidationError(_('Allowed file formats for photo IDs are jpeg, jpg, pdf or png'))
        if file_size >> 20 > 4 or (file_size >> 10 < 1 and file_extension == '.pdf') or (file_size >> 10 < 100 and file_extension != '.pdf') :
            raise ValidationError(_('Photo ID file size must be between 100kB (1kB for PDFs) and 4MB'))

    def _upload_photo_id(self, document_type, content, filename):
        # The request to be sent to Adyen will be different for Individuals,
        # Shareholders, etc. This method should be implemented by the models
        # inheriting this mixin
        raise NotImplementedError()


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
    payout_ids = fields.One2many('adyen.payout', 'adyen_account_id', string='Payouts')
    shareholder_ids = fields.One2many('adyen.shareholder', 'adyen_account_id', string='Shareholders')
    bank_account_ids = fields.One2many('adyen.bank.account', 'adyen_account_id', string='Bank Accounts')
    transaction_ids = fields.One2many('adyen.transaction', 'adyen_account_id', string='Transactions')
    transactions_count = fields.Integer(compute='_compute_transactions_count')

    is_business = fields.Boolean('Is a business', required=True)

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

    # KYC
    kyc_status = fields.Selection(string='KYC Status', selection=[
        ('awaiting_data', 'Data to provide'),
        ('pending', 'Waiting for validation'),
        ('passed', 'Confirmed'),
        ('failed', 'Failed'),
    ], required=True, default='pending')
    kyc_status_message = fields.Char('KYC Status Message', readonly=True)

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

    @api.model
    def create(self, values):
        adyen_account_id = super(AdyenAccount, self).create(values)
        self.env.company.adyen_account_id = adyen_account_id.id

        # Create account on odoo.com, proxy and Adyen
        response = adyen_account_id._adyen_rpc('create_account_holder', adyen_account_id._format_data())

        # Save adyen_uuid and proxy_token, that have been generated by odoo.com and the proxy
        adyen_account_id.with_context(update_from_adyen=True).write({
            'adyen_uuid': response['adyen_uuid'],
            'proxy_token': response['proxy_token'],
        })

        # A default payout is created for all adyen accounts
        adyen_account_id.env['adyen.payout'].with_context(update_from_adyen=True).create({
            'code': response['adyen_response']['accountCode'],
            'adyen_account_id': adyen_account_id.id,
        })
        return adyen_account_id

    def write(self, vals):
        res = super(AdyenAccount, self).write(vals)
        if not self.env.context.get('update_from_adyen'):
            self._adyen_rpc('update_account_holder', self._format_data())
        return res

    def unlink(self):
        for adyen_account_id in self:
            adyen_account_id._adyen_rpc('close_account_holder', {
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
        return_url = url_join(self.env['ir.config_parameter'].sudo().get_param('web.base.url'), 'adyen_platforms/create_account')
        onboarding_url = self.env['ir.config_parameter'].sudo().get_param('adyen_platforms.onboarding_url')
        return {
            'type': 'ir.actions.act_url',
            'url': url_join(onboarding_url, 'get_creation_token?return_url=%s' % return_url),
        }

    def action_show_transactions(self):
        return {
            'name': _('Transactions'),
            'view_mode': 'tree,form',
            'domain': [('adyen_account_id', '=', self.id)],
            'res_model': 'adyen.transaction',
            'type': 'ir.actions.act_window',
            'context': {'group_by': ['adyen_payout_id']}
        }

    def _upload_photo_id(self, document_type, content, filename):
        self._adyen_rpc('upload_document', {
            'documentDetail': {
                'accountHolderCode': self.account_holder_code,
                'documentType': document_type,
                'filename': filename,
            },
            'documentContent': content.decode(),
        })

    def _format_data(self):
        data = {
            'accountHolderCode': self.account_holder_code,
            'accountHolderDetails': {
                'address': {
                    'country': self.country_id.code,
                    'stateOrProvince': self.state_id.code or None,
                    'city': self.city,
                    'postalCode': self.zip,
                    'street': self.street,
                    'houseNumberOrName': self.house_number_or_name,
                },
                'email': self.email,
                'fullPhoneNumber': self.phone_number,
            },
            'legalEntity': 'Business' if self.is_business else 'Individual',
        }

        if self.is_business:
            data['accountHolderDetails']['businessDetails'] = {
                'legalBusinessName': self.legal_business_name,
                'doingBusinessAs': self.doing_business_as,
                'registrationNumber': self.registration_number,
            }
        else:
            data['accountHolderDetails']['individualDetails'] = {
                'name': {
                    'firstName': self.first_name,
                    'lastName': self.last_name,
                    'gender': 'UNKNOWN',
                },
                'personalData': {
                    'dateOfBirth': str(self.date_of_birth),
                }
            }

            # documentData cannot be present in the data if not set
            if self.document_number:
                data['accountHolderDetails']['individualDetails']['personalData']['documentData'] = [{
                    'number': self.document_number,
                    'type': self.document_type,
                }]

        return data

    def _adyen_rpc(self, operation, adyen_data={}):
        if operation == 'create_account_holder':
            url = self.env['ir.config_parameter'].sudo().get_param('adyen_platforms.onboarding_url')
            params = {
                'creation_token': request.session.get('adyen_creation_token'),
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
        except Exception as e:
            raise UserError(_('The Adyen proxy is not reachable, please try again later.'))
        response = req.json()

        if 'error' in response:
            name = response['error']['data'].get('name').rpartition('.')[-1]
            if name == 'ValidationError':
                raise ValidationError(response['error']['data'].get('arguments')[0])
            else:
                raise UserError(_("We had troubles reaching Adyen, please retry later or contact the support if the problem persists"))

        result = response.get('result')
        if 'verification' in result:
            self._update_kyc_status(result['verification'])

        return result

    @api.model
    def _sync_adyen_cron(self):
        self._sync_adyen_kyc_status()
        self.env['adyen.transaction'].sync_adyen_transactions()
        self.env['adyen.payout']._process_payouts()

    @api.model
    def _sync_adyen_kyc_status(self):
        for adyen_account_id in self.search([]):
            data = adyen_account_id._adyen_rpc('get_account_holder', {
                'accountHolderCode': adyen_account_id.account_holder_code,
            })
            adyen_account_id._update_kyc_status(data['verification'])

    def _update_kyc_status(self, checks):
        all_checks_status = []

        # Account Holder Checks
        account_holder_checks = checks.get('accountHolder', {})
        account_holder_messages = []
        for check in account_holder_checks.get('checks'):
            all_checks_status.append(check['status'])
            kyc_status_message = self._get_kyc_message(check)
            if kyc_status_message:
                account_holder_messages.append(kyc_status_message)

        # Shareholders Checks
        shareholder_checks = checks.get('shareholders', {})
        shareholder_messages = []
        kyc_status_message = False
        for sc in shareholder_checks:
            shareholder_status = []
            shareholder_id = self.shareholder_ids.filtered(lambda shareholder: shareholder.shareholder_uuid == sc['shareholderCode'])
            for check in sc.get('checks'):
                all_checks_status.append(check['status'])
                shareholder_status.append(check['status'])
                kyc_status_message = self._get_kyc_message(check)
                if kyc_status_message:
                    shareholder_messages.append('[%s] %s' % (shareholder_id.display_name, kyc_status_message))
            shareholder_id.with_context(update_from_adyen=True).write({
                'kyc_status': self.get_status(shareholder_status),
                'kyc_status_message': kyc_status_message,
            })

        # Bank Account Checks
        bank_account_checks = checks.get('bankAccounts', {})
        bank_account_messages = []
        kyc_status_message = False
        for bac in bank_account_checks:
            bank_account_status = []
            bank_account_id = self.bank_account_ids.filtered(lambda bank_account: bank_account.bank_account_uuid == bac['bankAccountUUID'])
            for check in bac.get('checks'):
                all_checks_status.append(check['status'])
                bank_account_status.append(check['status'])
                kyc_status_message = self._get_kyc_message(check)
                if kyc_status_message:
                    bank_account_messages.append('[%s] %s' % (bank_account_id.display_name, kyc_status_message))
            bank_account_id.with_context(update_from_adyen=True).write({
                'kyc_status': self.get_status(bank_account_status),
                'kyc_status_message': kyc_status_message,
            })

        kyc_status = self.get_status(all_checks_status)
        kyc_status_message = self.env['ir.qweb']._render('adyen_platforms.kyc_status_message', {
            'kyc_status': dict(self._fields['kyc_status'].selection)[kyc_status],
            'account_holder_messages': account_holder_messages,
            'shareholder_messages': shareholder_messages,
            'bank_account_messages': bank_account_messages,
        })

        if kyc_status_message.decode() != self.kyc_status_message:
            self.sudo().message_post(body = kyc_status_message, subtype_xmlid="mail.mt_comment") # Message from Odoo Bot

        self.with_context(update_from_adyen=True).write({
            'kyc_status': kyc_status,
            'kyc_status_message': kyc_status_message,
        })

    @api.model
    def get_status(self, statuses):
        if any(status in ['FAILED'] for status in statuses):
            return 'failed'
        if any(status in ['INVALID_DATA', 'RETRY_LIMIT_REACHED', 'AWAITING_DATA'] for status in statuses):
            return 'awaiting_data'
        if any(status in ['DATA_PROVIDED', 'PENDING'] for status in statuses):
            return 'pending'
        return 'passed'

    @api.model
    def _get_kyc_message(self, check):
        if check.get('summary', {}).get('kycCheckDescription'):
            return check['summary']['kycCheckDescription']
        if check.get('requiredFields', {}):
            return _('Missing required fields: ') + ', '.join(check.get('requiredFields'))
        return ''


class AdyenShareholder(models.Model):
    _name = 'adyen.shareholder'
    _inherit = ['adyen.id.mixin', 'adyen.address.mixin']
    _description = 'Adyen for Platforms Shareholder'
    _rec_name = 'full_name'

    adyen_account_id = fields.Many2one('adyen.account', ondelete='cascade')
    shareholder_reference = fields.Char('Reference', default=lambda self: uuid.uuid4().hex)
    shareholder_uuid = fields.Char('UUID') # Given by Adyen
    first_name = fields.Char('First Name', required=True)
    last_name = fields.Char('Last Name', required=True)
    full_name = fields.Char(compute='_compute_full_name')
    date_of_birth = fields.Date('Date of birth', required=True)
    document_number = fields.Char('ID Number', 
            help="The type of ID Number required depends on the country:\n"
             "US: Social Security Number (9 digits or last 4 digits)\n"
             "Canada: Social Insurance Number\nItaly: Codice fiscale\n"
             "Australia: Document Number")

    # KYC
    kyc_status = fields.Selection(string='KYC Status', selection=[
        ('awaiting_data', 'Data to provide'),
        ('pending', 'Waiting for validation'),
        ('passed', 'Confirmed'),
        ('failed', 'Failed'),
    ], required=True, default='pending')
    kyc_status_message = fields.Char('KYC Status Message', readonly=True)

    @api.depends('first_name', 'last_name')
    def _compute_full_name(self):
        for adyen_shareholder_id in self:
            adyen_shareholder_id.full_name = '%s %s' % (adyen_shareholder_id.first_name, adyen_shareholder_id.last_name)

    @api.model
    def create(self, values):
        adyen_shareholder_id = super(AdyenShareholder, self).create(values)
        response = adyen_shareholder_id.adyen_account_id._adyen_rpc('update_account_holder', adyen_shareholder_id._format_data())
        shareholders = response['accountHolderDetails']['businessDetails']['shareholders']
        created_shareholder = next(shareholder for shareholder in shareholders if shareholder['shareholderReference'] == adyen_shareholder_id.shareholder_reference)
        adyen_shareholder_id.with_context(update_from_adyen=True).write({
            'shareholder_uuid': created_shareholder['shareholderCode'],
        })
        return adyen_shareholder_id

    def write(self, vals):
        res = super(AdyenShareholder, self).write(vals)
        if not self.env.context.get('update_from_adyen'):
            self.adyen_account_id._adyen_rpc('update_account_holder', self._format_data())
        return res

    def unlink(self):
        for shareholder_id in self:
            shareholder_id.adyen_account_id._adyen_rpc('delete_shareholders', {
                'accountHolderCode': shareholder_id.adyen_account_id.account_holder_code,
                'shareholderCodes': [shareholder_id.shareholder_uuid],
            })
        return super(AdyenShareholder, self).unlink()

    def _upload_photo_id(self, document_type, content, filename):
        self.adyen_account_id._adyen_rpc('upload_document', {
            'documentDetail': {
                'accountHolderCode': self.adyen_account_id.account_holder_code,
                'shareholderCode': self.shareholder_uuid,
                'documentType': document_type,
                'filename': filename,
            },
            'documentContent': content.decode(),
        })

    def _format_data(self):
        data = {
            'accountHolderCode': self.adyen_account_id.account_holder_code,
            'accountHolderDetails': {
                'businessDetails': {
                    'shareholders': [{
                        'shareholderCode': self.shareholder_uuid or None,
                        'shareholderReference': self.shareholder_reference,
                        'address': {
                            'city': self.city,
                            'country': self.country_code,
                            'houseNumberOrName': self.house_number_or_name,
                            'postalCode': self.zip,
                            'stateOrProvince': self.state_id.code or None,
                            'street': self.street,
                        },
                        'name': {
                            'firstName': self.first_name,
                            'lastName': self.last_name,
                            'gender': 'UNKNOWN'
                        },
                        'personalData': {
                            'dateOfBirth': str(self.date_of_birth),
                        }
                    }]
                }
            }
        }

        # documentData cannot be present in the data if not set
        if self.document_number:
            data['accountHolderDetails']['businessDetails']['shareholders'][0]['personalData']['documentData'] = [{
                'number': self.document_number,
                'type': 'ID',
            }]

        return data

class AdyenBankAccount(models.Model):
    _name = 'adyen.bank.account'
    _description = 'Adyen for Platforms Bank Account'

    adyen_account_id = fields.Many2one('adyen.account', ondelete='cascade')
    bank_account_reference = fields.Char('Reference', default=lambda self: uuid.uuid4().hex)
    bank_account_uuid = fields.Char('UUID') # Given by Adyen
    owner_name = fields.Char('Owner Name', required=True)
    country_id = fields.Many2one('res.country', string='Country', domain=[('code', 'in', ADYEN_AVAILABLE_COUNTRIES)], required=True)
    country_code = fields.Char(related='country_id.code')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True)
    iban = fields.Char('IBAN')
    account_number = fields.Char('Account Number')
    branch_code = fields.Char('Branch Code')
    bank_code = fields.Char('Bank Code')
    account_type = fields.Selection(string='Account Type', selection=[
        ('checking', 'Checking'),
        ('savings', 'Savings'),
    ])
    owner_country_id = fields.Many2one('res.country', string='Owner Country')
    owner_state_id = fields.Many2one('res.country.state', 'Owner State', domain="[('country_id', '=?', owner_country_id)]")
    owner_street = fields.Char('Owner Street')
    owner_city = fields.Char('Owner City')
    owner_zip = fields.Char('Owner ZIP')
    owner_house_number_or_name = fields.Char('Owner House Number or Name')

    bank_statement = fields.Binary('Bank Statement', help="You need to provide a bank statement to allow payouts. \
        The file must be a bank statement, a screenshot of your online banking environment, a letter from the bank or a cheque and must contain \
        the logo of the bank or it's name in a unique font, the bank account details, the name of the account holder.\
        Allowed formats: jpg, pdf, png. Maximum allowed size: 10MB.")
    bank_statement_filename = fields.Char()

    # KYC
    kyc_status = fields.Selection(string='KYC Status', selection=[
        ('awaiting_data', 'Data to provide'),
        ('pending', 'Waiting for validation'),
        ('passed', 'Confirmed'),
        ('failed', 'Failed'),
    ], required=True, default='pending')
    kyc_status_message = fields.Char('KYC Status Message', readonly=True)

    @api.model
    def create(self, values):
        adyen_bank_account_id = super(AdyenBankAccount, self).create(values)
        response = adyen_bank_account_id.adyen_account_id._adyen_rpc('update_account_holder', adyen_bank_account_id._format_data())
        bank_accounts = response['accountHolderDetails']['bankAccountDetails']
        created_bank_account = next(bank_account for bank_account in bank_accounts if bank_account['bankAccountReference'] == adyen_bank_account_id.bank_account_reference)
        adyen_bank_account_id.with_context(update_from_adyen=True).write({
            'bank_account_uuid': created_bank_account['bankAccountUUID'],
        })
        return adyen_bank_account_id

    def write(self, vals):
        res = super(AdyenBankAccount, self).write(vals)
        if not self.env.context.get('update_from_adyen'):
            self.adyen_account_id._adyen_rpc('update_account_holder', self._format_data())
        if 'bank_statement' in vals:
            self._upload_bank_statement(vals['bank_statement'], vals['bank_statement_filename'])
        return res

    def unlink(self):
        for bank_account_id in self:
            bank_account_id.adyen_account_id._adyen_rpc('delete_bank_accounts', {
                'accountHolderCode': bank_account_id.adyen_account_id.account_holder_code,
                'bankAccountUUIDs': [bank_account_id.bank_account_uuid],
            })
        return super(AdyenBankAccount, self).unlink()

    def _format_data(self):
        return {
            'accountHolderCode': self.adyen_account_id.account_holder_code,
            'accountHolderDetails': {
                'bankAccountDetails': [{
                    'accountNumber': self.account_number or None,
                    'accountType': self.account_type or None,
                    'bankAccountReference': self.bank_account_reference,
                    'bankAccountUUID': self.bank_account_uuid or None,
                    'bankCode': self.bank_code or None,
                    'branchCode': self.branch_code or None,
                    'countryCode': self.country_code,
                    'currencyCode': self.currency_id.name,
                    'iban': self.iban or None,
                    'ownerCity': self.owner_city or None,
                    'ownerCountryCode': self.owner_country_id.code or None,
                    'ownerHouseNumberOrName': self.owner_house_number_or_name or None,
                    'ownerName': self.owner_name,
                    'ownerPostalCode': self.owner_zip or None,
                    'ownerState': self.owner_state_id.code or None,
                    'ownerStreet': self.owner_street or None,
                }],
            }
        }

    def _upload_bank_statement(self, content, filename):
        file_extension = os.path.splitext(filename)[1]
        file_size = len(content.encode('utf-8'))
        if file_extension not in ['.jpeg', '.jpg', '.pdf', '.png']:
            raise ValidationError(_('Allowed file formats for bank statements are jpeg, jpg, pdf or png'))
        if file_size >> 20 > 10 or (file_size >> 10 < 10 and file_extension != '.pdf') :
            raise ValidationError(_('Bank statements must be greater than 10kB (except for PDFs) and smaller than 10MB'))

        self.adyen_account_id._adyen_rpc('upload_document', {
            'documentDetail': {
                'accountHolderCode': self.adyen_account_id.account_holder_code,
                'bankAccountUUID': self.bank_account_uuid,
                'documentType': 'BANK_STATEMENT',
                'filename': filename,
            },
            'documentContent': content,
        })


class AdyenPayout(models.Model):
    _name = 'adyen.payout'
    _description = 'Adyen for Platforms Payout'

    @api.depends('payout_schedule')
    def _compute_next_scheduled_payout(self):
        today = fields.date.today()
        for adyen_payout_id in self:
            adyen_payout_id.next_scheduled_payout = date_utils.end_of(today, adyen_payout_id.payout_schedule)

    adyen_account_id = fields.Many2one('adyen.account', ondelete='cascade')
    adyen_bank_account_id = fields.Many2one('adyen.bank.account', string='Bank Account',
        help='The bank account to which the payout is to be made. If left blank, a bank account is automatically selected')
    name = fields.Char('Name', default='Default', required=True)
    code = fields.Char('Account Code')
    payout_schedule = fields.Selection(string='Schedule', selection=[
        ('day', 'Daily'),
        ('week', 'Weekly'),
        ('month', 'Monthly'),
    ], default='week', required=True)
    next_scheduled_payout = fields.Date('Next scheduled payout', compute=_compute_next_scheduled_payout, store=True)
    transaction_ids = fields.One2many('adyen.transaction', 'adyen_payout_id', string='Transactions')

    @api.model
    def create(self, values):
        adyen_payout_id = super(AdyenPayout, self).create(values)
        if not adyen_payout_id.env.context.get('update_from_adyen'):
            response = adyen_payout_id.adyen_account_id._adyen_rpc('create_payout', {
                'accountHolderCode': adyen_payout_id.adyen_account_id.account_holder_code,
            })
            adyen_payout_id.with_context(update_from_adyen=True).write({
                'code': response['accountCode'],
            })
        return adyen_payout_id

    def unlink(self):
        for adyen_payout_id in self:
            adyen_payout_id.adyen_account_id._adyen_rpc('close_payout', {
                'accountCode': adyen_payout_id.code,
            })
        return super(AdyenPayout, self).unlink()

    @api.model
    def _process_payouts(self):
        for adyen_payout_id in self.search([('next_scheduled_payout', '<', fields.Date.today())]):
            adyen_payout_id.send_payout_request(notify=False)
            adyen_payout_id._compute_next_scheduled_payout()

    def send_payout_request(self, notify=True):
        response = self.adyen_account_id._adyen_rpc('account_holder_balance', {
            'accountHolderCode': self.adyen_account_id.account_holder_code,
        })
        balances = next(account_balance['detailBalance']['balance'] for account_balance in response['balancePerAccount'] if account_balance['accountCode'] == self.code)
        if notify and not balances:
            self.env['bus.bus'].sendone(
                (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
                {'type': 'simple_notification', 'title': _('No pending balance'), 'message': _('No balance is currently awaitng payout.')}
            )
        for balance in balances:
            response = self.adyen_account_id._adyen_rpc('payout_request', {
                'accountCode': self.code,
                'accountHolderCode': self.adyen_account_id.account_holder_code,
                'bankAccountUUID': self.adyen_bank_account_id.bank_account_uuid or None,
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

    def _fetch_transactions(self, page=1):
        response = self.adyen_account_id._adyen_rpc('get_transactions', {
            'accountHolderCode': self.adyen_account_id.account_holder_code,
            'transactionListsPerAccount': [{
                'accountCode': self.code,
                'page': page,
            }]
        })
        transaction_list = response['accountTransactionLists'][0]
        return transaction_list['transactions'], transaction_list['hasNextPage']
