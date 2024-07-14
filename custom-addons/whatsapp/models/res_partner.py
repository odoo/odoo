# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re

from odoo import exceptions, models, _
from odoo.addons.phone_validation.tools import phone_validation
from odoo.addons.whatsapp.tools import phone_validation as phone_validation_wa

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _find_or_create_from_number(self, number, name=False):
        """ Number should come currently from whatsapp and contain country info. """
        search_number = number if number.startswith('+') else f'+{number}'
        try:
            formatted_number = phone_validation_wa.wa_phone_format(
                self.env.company,
                number=search_number,
                force_format='E164',
                raise_exception=True,
            )
        except Exception:  # noqa: BLE001 don't want to crash in that point, whatever the issue
            _logger.warning('WhatsApp: impossible to format incoming number %s, skipping partner creation', number)
            formatted_number = False
        if not number or not formatted_number:
            return self.env['res.partner']

        # find country / local number based on formatted number to ease future searches
        region_data = phone_validation.phone_get_region_data_for_number(formatted_number)
        number_country_code = region_data['code']
        number_national_number = str(region_data['national_number'])
        number_phone_code = int(region_data['phone_code'])

        # search partner on INTL number, then fallback on national number
        partners = self._search_on_phone_mobile("=", formatted_number)
        if not partners:
            partners = self._search_on_phone_mobile("=like", number_national_number)

        if not partners:
            # do not set a country if country code is not unique as we cannot guess
            country = self.env['res.country'].search([('phone_code', '=', number_phone_code)])
            if len(country) > 1:
                country = country.filtered(lambda c: c.code.lower() == number_country_code.lower())

            partners = self.env['res.partner'].create({
                'country_id': country.id if country and len(country) == 1 else False,
                'mobile': formatted_number,
                'name': name or formatted_number,
            })
            partners._message_log(
                body=_("Partner created by incoming WhatsApp message.")
            )
        return partners[0]

    def _search_on_phone_mobile(self, operator, number):
        """ Temporary hackish solution to better find partners based on numbers.
        It is globally copied from '_search_phone_mobile_search' defined on
        'mail.thread.phone' mixin. However a design decision led to not using
        it in base whatsapp module (because stuff), hence not having
        this search method nor the 'phone_sanitized' field. """
        assert operator in {'=', '=like'}
        number = number.strip()
        if not number:
            return self.browse()
        if len(number) < self.env['mail.thread.phone']._phone_search_min_length:
            raise exceptions.UserError(
                _('Please enter at least 3 characters when searching a Phone/Mobile number.')
            )

        phone_fields = ['mobile', 'phone']
        pattern = r'[\s\\./\(\)\-]'
        sql_operator = "LIKE" if operator == "=like" else "="

        if number.startswith(('+', '00')):
            # searching on +32485112233 should also finds 0032485112233 (and vice versa)
            # we therefore remove it from input value and search for both of them in db
            where_str = ' OR '.join(
                f"""partner.{phone_field} IS NOT NULL AND (
                        REGEXP_REPLACE(partner.{phone_field}, %s, '', 'g') {sql_operator} %s OR
                        REGEXP_REPLACE(partner.{phone_field}, %s, '', 'g') {sql_operator} %s
                )"""
                for phone_field in phone_fields
            )
            query = f"SELECT partner.id FROM {self._table} partner WHERE {where_str};"

            term = re.sub(pattern, '', number[1 if number.startswith('+') else 2:])
            if operator == "=like":
                term = f'%{term}'
            self._cr.execute(
                query, (pattern, '00' + term, pattern, '+' + term) * len(phone_fields)
            )
        else:
            where_str = ' OR '.join(
                f"(partner.{phone_field} IS NOT NULL AND REGEXP_REPLACE(partner.{phone_field}, %s, '', 'g') {sql_operator} %s)"
                for phone_field in phone_fields
            )
            query = f"SELECT partner.id FROM {self._table} partner WHERE {where_str};"
            term = re.sub(pattern, '', number)
            if operator == "=like":
                term = f'%{term}'
            self._cr.execute(query, (pattern, term) * len(phone_fields))
        res = self._cr.fetchall()
        return self.browse([r[0] for r in res])
