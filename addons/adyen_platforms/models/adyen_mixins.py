# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.mimetypes import guess_mimetype

ADYEN_AVAILABLE_COUNTRIES = [
    'US', 'AT', 'AU', 'BE', 'CA', 'CH', 'CZ', 'DE', 'ES', 'FI', 'FR', 'GB', 'GR', 'HR', 'IE', 'IT',
    'LT', 'LU', 'NL', 'PL', 'PT'
]


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
        res = super().write(vals)

        # Check file formats
        if vals.get('id_front'):
            self._check_file_requirements(vals.get('id_front'))
        if vals.get('id_back'):
            self._check_file_requirements(vals.get('id_back'))

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
    def _check_file_requirements(self, content):
        content_encoded = content.encode('utf8')
        mimetype = guess_mimetype(base64.b64decode(content_encoded))
        file_size = len(content_encoded)

        # Document requirements: https://docs.adyen.com/platforms/verification-checks/photo-id-check#requirements
        if mimetype not in ['image/jpeg', 'image/png', 'application/pdf']:
            raise ValidationError(_('Allowed file formats for photo IDs are jpeg, jpg, pdf or png'))
        if file_size < (100 * 1024) or (file_size < 1024 and mimetype == 'application/pdf'):
            raise ValidationError(_('Minimum allowed size for photo ID: 1 KB for PDF, 100 KB for other formats.'))
        if file_size > (4 * 1024 * 1024):
            raise ValidationError(_('Maximum allowed size for photo ID: 4 MB.'))

    def _upload_photo_id(self, document_type, content, filename):
        # The request to be sent to Adyen will be different for Individuals,
        # Shareholders, etc. This method should be implemented by the models
        # inheriting this mixin
        raise NotImplementedError()
