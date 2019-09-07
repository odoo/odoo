# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons.phone_validation.tools import phone_validation


class PhoneValidationMixin(models.AbstractModel):
    _name = 'phone.validation.mixin'
    _description = 'Phone Validation Mixin'

    def _phone_get_country_field(self):
        if 'country_id' in self:
            return 'country_id'
        return False

    def _phone_get_country(self):
        if 'country_id' in self and self.country_id:
            return self.country_id
        return self.env.company.country_id

    def phone_format(self, number, country=None, company=None):
        country = country or self._phone_get_country()
        if not country:
            return number
        return phone_validation.phone_format(
            number,
            country.code if country else None,
            country.phone_code if country else None,
            force_format='INTERNATIONAL',
            raise_exception=False
        )

    def phone_get_sanitized_numbers(self, number_fname='mobile', force_format='E164'):
        res = dict.fromkeys(self.ids, False)
        country_fname = self._phone_get_country_field()
        for record in self:
            number = record[number_fname]
            res[record.id] = phone_validation.phone_sanitize_numbers_w_record([number], record, record_country_fname=country_fname, force_format=force_format)[number]['sanitized']
        return res

    def phone_get_sanitized_number(self, number_fname='mobile', force_format='E164'):
        self.ensure_one()
        country_fname = self._phone_get_country_field()
        number = self[number_fname]
        return phone_validation.phone_sanitize_numbers_w_record([number], self, record_country_fname=country_fname, force_format=force_format)[number]['sanitized']
