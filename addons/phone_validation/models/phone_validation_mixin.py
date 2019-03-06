# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons.phone_validation.tools import phone_validation


class PhoneValidationMixin(models.AbstractModel):
    _name = 'phone.validation.mixin'
    _description = 'Phone Validation Mixin'

    def _phone_get_country(self):
        if 'country_id' in self and self.country_id:
            return self.country_id
        return self.env.user.company_id.country_id

    def _phone_get_always_international(self):
        if 'company_id' in self and self.company_id:
            return self.company_id.phone_international_format == 'prefix'
        return self.env.user.company_id.phone_international_format == 'prefix'

    def phone_format(self, number, country=None, company=None):
        country = country or self._phone_get_country()
        if not country:
            return number
        always_international = company.phone_international_format == 'prefix' if company else self._phone_get_always_international()
        return phone_validation.phone_format(
            number,
            country.code if country else None,
            country.phone_code if country else None,
            always_international=always_international,
            raise_exception=False
        )
