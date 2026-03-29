# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.addons.phone_validation.tools import phone_validation


class Partner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner']

    @api.onchange('phone', 'country_id', 'company_id')
    def _onchange_phone_validation(self):
        if self.phone:
            self.phone = self._phone_format(self.phone)

    @api.onchange('mobile', 'country_id', 'company_id')
    def _onchange_mobile_validation(self):
        if self.mobile:
            self.mobile = self._phone_format(self.mobile)

    def _phone_format(self, number, country=None, company=None):
        country = country or self.country_id or self.env.company.country_id
        if not country:
            return number
        return phone_validation.phone_format(
            number,
            country.code if country else None,
            country.phone_code if country else None,
            force_format='INTERNATIONAL',
            raise_exception=False
        )

    def phone_get_sanitized_number(self, number_fname='mobile', force_format='E164'):
        """ Stand alone version, allowing to use it on partner model without
        having any dependency on sms module. To cleanup in master (15.3 +)."""
        self.ensure_one()
        country_fname = 'country_id'
        number = self[number_fname]
        return phone_validation.phone_sanitize_numbers_w_record([number], self, record_country_fname=country_fname, force_format=force_format)[number]['sanitized']

    def _phone_get_number_fields(self):
        """ Stand alone version, allowing to use it on partner model without
        having any dependency on sms module. To cleanup in master (15.3 +)."""
        return ['mobile', 'phone']
