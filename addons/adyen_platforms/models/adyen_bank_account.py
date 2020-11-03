# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import uuid

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.mimetypes import guess_mimetype

from odoo.addons.adyen_platforms.models.adyen_kyc import ADYEN_KYC_STATUS
from odoo.addons.adyen_platforms.models.adyen_mixins import ADYEN_AVAILABLE_COUNTRIES


class AdyenBankAccount(models.Model):
    _name = 'adyen.bank.account'
    _description = 'Adyen for Platforms Bank Account'

    adyen_account_id = fields.Many2one('adyen.account', ondelete='cascade')
    bank_account_reference = fields.Char('Reference', default=lambda self: uuid.uuid4().hex)
    bank_account_uuid = fields.Char('UUID')  # Given by Adyen
    owner_name = fields.Char('Owner Name', required=True)
    country_id = fields.Many2one('res.country', string='Country', domain=[('code', 'in', ADYEN_AVAILABLE_COUNTRIES)], required=True)
    country_code = fields.Char(related='country_id.code')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True)
    currency_name = fields.Char(related='currency_id.name', string='Currency Name')
    iban = fields.Char('IBAN')
    account_number = fields.Char('Account Number')
    branch_code = fields.Char('Branch Code')
    bank_city = fields.Char('Bank City')
    bank_code = fields.Char('Bank Code')
    bank_name = fields.Char('Bank Name')
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
    adyen_kyc_ids = fields.One2many('adyen.kyc', 'bank_account_id')
    kyc_status = fields.Selection(ADYEN_KYC_STATUS, compute='_compute_kyc_status', readonly=True)
    kyc_status_message = fields.Char(compute='_compute_kyc_status', readonly=True)

    @api.depends_context('lang')
    @api.depends('adyen_kyc_ids')
    def _compute_kyc_status(self):
        self.kyc_status_message = False
        self.kyc_status = False
        for bank_account in self.filtered('adyen_kyc_ids'):
            kyc = bank_account.adyen_kyc_ids._sort_by_status()
            bank_account.kyc_status = kyc[0].status

    @api.model
    def create(self, values):
        adyen_bank_account_id = super().create(values)
        adyen_account_id = self.env['adyen.account'].browse(values.get('adyen_account_id'))
        response = adyen_account_id._adyen_rpc('v1/update_account_holder', self._format_data(values))
        bank_accounts = response['accountHolderDetails']['bankAccountDetails']

        created_bank_account = next(bank_account for bank_account in bank_accounts if bank_account['bankAccountReference'] == adyen_bank_account_id.bank_account_reference)
        adyen_bank_account_id.with_context(update_from_adyen=True).write({
            'bank_account_uuid': created_bank_account['bankAccountUUID'],
        })
        return adyen_bank_account_id

    def write(self, vals):
        res = super().write(vals)

        if not self.env.context.get('update_from_adyen'):
            self.adyen_account_id._adyen_rpc('v1/update_account_holder', self._format_data(vals))
        if 'bank_statement' in vals:
            self._upload_bank_statement(vals['bank_statement'], vals['bank_statement_filename'])
        return res

    def unlink(self):
        self.check_access_rights('unlink')

        for bank_account_id in self:
            bank_account_id.adyen_account_id._adyen_rpc('v1/delete_bank_accounts', {
                'accountHolderCode': bank_account_id.adyen_account_id.account_holder_code,
                'bankAccountUUIDs': [bank_account_id.bank_account_uuid],
            })
        return super().unlink()

    def name_get(self):
        res = []
        for bank_account in self:
            name = f'{bank_account.owner_name} - f{bank_account.iban or bank_account.account_number}'
            res.append((bank_account.id, name))
        return res

    def _format_data(self, values=None):
        if values is None:
            values = {}
        adyen_account_id = self.env['adyen.account'].browse(values.get('adyen_account_id')) if values.get('adyen_account_id') else self.adyen_account_id
        country_id = self.env['res.country'].browse(values.get('country_id')) if values.get('country_id') else self.country_id
        currency_id = self.env['res.currency'].browse(values.get('currency_id')) if values.get('currency_id') else self.currency_id
        owner_country_id = self.env['res.country'].browse(values.get('owner_country_id')) if values.get('owner_country_id') else self.owner_country_id
        owner_state_id = self.env['res.country.state'].browse(values.get('owner_state_id')) if values.get('owner_state_id') else self.owner_state_id
        return {
            'accountHolderCode': adyen_account_id.account_holder_code,
            'accountHolderDetails': {
                'bankAccountDetails': [{
                    'accountNumber': values.get('account_number') or self.account_number or None,
                    'accountType': values.get('account_type') or self.account_type or None,
                    'bankAccountReference': values.get('bank_account_reference') or self.bank_account_reference,
                    'bankAccountUUID': values.get('bank_account_uuid') or self.bank_account_uuid or None,
                    'bankCity': values.get('bank_city') or self.bank_city or None,
                    'bankCode': values.get('bank_code') or self.bank_code or None,
                    'bankName': values.get('bank_name') or self.bank_name or None,
                    'branchCode': values.get('branch_code') or self.branch_code or None,
                    'countryCode': country_id.code,
                    'currencyCode': currency_id.name,
                    'iban': values.get('iban') or self.iban or None,
                    'ownerCity': values.get('owner_city') or self.owner_city or None,
                    'ownerCountryCode': owner_country_id.code or None,
                    'ownerHouseNumberOrName': values.get('owner_house_number_or_name') or self.owner_house_number_or_name or None,
                    'ownerName': values.get('owner_name') or self.owner_name,
                    'ownerPostalCode': values.get('owner_zip') or self.owner_zip or None,
                    'ownerState': owner_state_id.code or None,
                    'ownerStreet': values.get('owner_street') or self.owner_street or None,
                }],
            }
        }

    def _upload_bank_statement(self, content, filename):
        content_encoded = content.encode('utf8')
        mimetype = guess_mimetype(base64.b64decode(content_encoded))
        file_size = len(content_encoded)

        # Document requirements: https://docs.adyen.com/platforms/verification-checks/bank-account-check#requirements
        if mimetype not in ['image/jpeg', 'image/png', 'application/pdf']:
            raise ValidationError(_('Allowed file formats for bank statements are jpeg, jpg, pdf or png. Received %r instead.', mimetype))
        if file_size < (100 * 1024) or (file_size < 1024 and mimetype == 'application/pdf'):
            raise ValidationError(_('Minimum allowed size for bank statements: 1 KB for PDF, 100 KB for other formats.'))
        if file_size > (4 * 1024 * 1024):
            raise ValidationError(_('Maximum allowed size for bank statements: 4MB.'))

        test_mode = self.env['ir.config_parameter'].sudo().get_param('adyen_platforms.test_mode')
        self.adyen_account_id._adyen_rpc('v1/upload_document', {
            'documentDetail': {
                'accountHolderCode': self.adyen_account_id.account_holder_code,
                'bankAccountUUID': self.bank_account_uuid,
                'documentType': 'BANK_STATEMENT',
                'filename': filename,
                'description': 'PASSED' if test_mode else '',
            },
            'documentContent': content,
        })
