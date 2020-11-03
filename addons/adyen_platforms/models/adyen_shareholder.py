# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid

from odoo import api, fields, models

from odoo.addons.adyen_platforms.models.adyen_kyc import ADYEN_KYC_STATUS


class AdyenShareholder(models.Model):
    _name = 'adyen.shareholder'
    _inherit = ['adyen.id.mixin', 'adyen.address.mixin']
    _description = 'Adyen for Platforms Shareholder'
    _rec_name = 'full_name'

    adyen_account_id = fields.Many2one('adyen.account', ondelete='cascade')
    shareholder_reference = fields.Char('Reference', default=lambda self: uuid.uuid4().hex)
    shareholder_uuid = fields.Char('UUID')  # Given by Adyen
    first_name = fields.Char('First Name', required=True)
    last_name = fields.Char('Last Name', required=True)
    full_name = fields.Char(compute='_compute_full_name')
    date_of_birth = fields.Date('Date of birth', required=True)
    document_number = fields.Char('ID Number',
            help="The type of ID Number required depends on the country:\n"
             "US: Social Security Number (9 digits or last 4 digits)\n"
             "Canada: Social Insurance Number\nItaly: Codice fiscale\n"
             "Australia: Document Number")

    adyen_kyc_ids = fields.One2many('adyen.kyc', 'shareholder_id')
    kyc_status = fields.Selection(ADYEN_KYC_STATUS, compute='_compute_kyc_status', readonly=True)
    kyc_status_message = fields.Char(compute='_compute_kyc_status', readonly=True)

    @api.depends_context('lang')
    @api.depends('adyen_kyc_ids')
    def _compute_kyc_status(self):
        self.kyc_status_message = False
        self.kyc_status = False
        for shareholder in self.filtered('adyen_kyc_ids'):
            kyc = shareholder.adyen_kyc_ids._sort_by_status()
            shareholder.kyc_status = kyc[0].status

    @api.depends('first_name', 'last_name')
    def _compute_full_name(self):
        for adyen_shareholder_id in self:
            adyen_shareholder_id.full_name = f'{adyen_shareholder_id.first_name} {adyen_shareholder_id.last_name}'

    @api.model
    def create(self, values):
        adyen_shareholder_id = super().create(values)
        adyen_account_id = self.env['adyen.account'].browse(values.get('adyen_account_id'))
        response = adyen_account_id._adyen_rpc('v1/update_account_holder', self._format_data(values))

        shareholders = response['accountHolderDetails']['businessDetails']['shareholders']
        created_shareholder = next(shareholder for shareholder in shareholders if shareholder['shareholderReference'] == adyen_shareholder_id.shareholder_reference)
        adyen_shareholder_id.with_context(update_from_adyen=True).write({
            'shareholder_uuid': created_shareholder['shareholderCode'],
        })
        return adyen_shareholder_id

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('update_from_adyen'):
            self.adyen_account_id._adyen_rpc('v1/update_account_holder', self._format_data(vals))
        return res

    def unlink(self):
        self.check_access_rights('unlink')

        for shareholder_id in self:
            shareholder_id.adyen_account_id._adyen_rpc('v1/delete_shareholders', {
                'accountHolderCode': shareholder_id.adyen_account_id.account_holder_code,
                'shareholderCodes': [shareholder_id.shareholder_uuid],
            })
        return super().unlink()

    def _upload_photo_id(self, document_type, content, filename):
        test_mode = self.env['ir.config_parameter'].sudo().get_param('adyen_platforms.test_mode')
        self.adyen_account_id._adyen_rpc('v1/upload_document', {
            'documentDetail': {
                'accountHolderCode': self.adyen_account_id.account_holder_code,
                'shareholderCode': self.shareholder_uuid,
                'documentType': document_type,
                'filename': filename,
                'description': 'PASSED' if test_mode else '',
            },
            'documentContent': content.decode(),
        })

    def _format_data(self, values):
        adyen_account_id = self.env['adyen.account'].browse(values.get('adyen_account_id')) if values.get('adyen_account_id') else self.adyen_account_id
        country_id = self.env['res.country'].browse(values.get('country_id')) if values.get('country_id') else self.country_id
        state_id = self.env['res.country.state'].browse(values.get('owner_state_id')) if values.get('state_id') else self.state_id
        data = {
            'accountHolderCode': adyen_account_id.account_holder_code,
            'accountHolderDetails': {
                'businessDetails': {
                    'shareholders': [{
                        'shareholderCode': values.get('shareholder_uuid') or self.shareholder_uuid or None,
                        'shareholderReference': values.get('shareholder_reference') or self.shareholder_reference,
                        'address': {
                            'city': values.get('city') or self.city,
                            'country': country_id.code,
                            'houseNumberOrName': values.get('house_number_or_name') or self.house_number_or_name,
                            'postalCode': values.get('zip') or self.zip,
                            'stateOrProvince': state_id.code or None,
                            'street': values.get('street') or self.street,
                        },
                        'name': {
                            'firstName': values.get('first_name') or self.first_name,
                            'lastName': values.get('last_name') or self.last_name,
                            'gender': 'UNKNOWN'
                        },
                        'personalData': {
                            'dateOfBirth': str(values.get('date_of_birth') or self.date_of_birth),
                        }
                    }]
                }
            }
        }

        # documentData cannot be present in the data if not set
        document_number = values.get('document_number') or self.document_number
        if document_number:
            data['accountHolderDetails']['businessDetails']['shareholders'][0]['personalData']['documentData'] = [{
                'number': document_number,
                'type': 'ID',
            }]

        return data
