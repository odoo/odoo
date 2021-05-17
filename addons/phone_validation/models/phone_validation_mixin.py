# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _
from odoo.exceptions import UserError
from odoo.addons.phone_validation.tools import phone_validation


class PhoneValidationMixin(models.AbstractModel):
    _name = 'phone.validation.mixin'
    _description = 'Phone Validation Mixin'

    def _search_phone_mobile_search(self, value, field_name):
        if len(value) <= 2:
            raise UserError(_('Please enter at least 3 digits when searching on phone / mobile.'))

        # searching on +32485112233 shouldonvert the search on real ids in the case it was asked on virtual ids, then call superalso finds 00485112233 (00 / + prefix are both valid)
        # we therefore remove it from input value and search for both of them in db
        if value.startswith('+') or value.startswith('00'):
            value = value.replace('+', '').replace('00', '', 1)
            starts_with = '(00|\+)'
        else:
            starts_with = '%'

        query = f"""
                SELECT model.id
                FROM {self._table} model
                WHERE REGEXP_REPLACE(model.{field_name}, '[^\d+]+', '', 'g') SIMILAR TO CONCAT(%s, REGEXP_REPLACE(%s, '\D+', '', 'g'), '%%')
            """

        self._cr.execute(query, (starts_with, value))
        res = self._cr.fetchall()
        if not res:
            return (0, '=', 1)
        return ('id', 'in', [r[0] for r in res])

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        """ Overide search to use improved search for ilike phone/mobile"""
        args = list(args)
        if any([leaf for leaf in args if leaf[0] in ["phone", 'mobile'] and leaf[1] == "ilike"]):
            for index in range(len(args)):
                if args[index][0] in ["phone", 'mobile'] and args[index][1] == "ilike":
                    args[index] = self._search_phone_mobile_search(args[index][2], args[index][0])
        return super(PhoneValidationMixin, self)._search(args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)

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
