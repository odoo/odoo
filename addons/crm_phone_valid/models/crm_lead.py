# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError

# Skip if the phonenumber Python module is not installed
try:

    import phonenumbers

    class FormatPhoneMixin(object):
        def _check_phone(self, phone):
            if not phone:
                return phone
            try:
                country = self.country_id and self.country_id.code or self.env.user.company_id.country_id.code or False
                nbr = phonenumbers.parse(phone, country)
            except Exception, e:
                raise UserError(_('Unable to parse the phone number!'))
            if not phonenumbers.is_possible_number(nbr):
                raise UserError(_('Invalid phone number, too few or too much digits!'))
            if not phonenumbers.is_valid_number(nbr):
                raise UserError(_('Invalid phone number, the prefix does not belong to a valid NPA!'))
            fmt = phonenumbers.PhoneNumberFormat.INTERNATIONAL
            if nbr.country_code == self.env.user.company_id.country_id.phone_code:
                fmt = phonenumbers.PhoneNumberFormat.NATIONAL
            nbr2 = phonenumbers.format_number(nbr, fmt)
            return nbr2

    class CRMLead(models.Model, FormatPhoneMixin):
        _inherit = "crm.lead"

        @api.onchange('phone')
        def phone_validate(self):
            self.phone = self._check_phone(self.phone)

        @api.onchange('mobile')
        def mobile_validate(self):
            self.mobile = self._check_phone(self.mobile)

    class ResPartner(models.Model, FormatPhoneMixin):
        _inherit = "res.partner"

        @api.onchange('phone')
        def phone_validate(self):
            self.phone = self._check_phone(self.phone)

        @api.onchange('mobile')
        def mobile_validate(self):
            self.mobile = self._check_phone(self.mobile)

        @api.onchange('fax')
        def mobile_validate(self):
            self.fax = self._check_phone(self.fax)


except ImportError, e:
    _logger.warning("The `phonenumbers` Python module is not installed, phone numbers will not be verified. Try: pip install phonenumbers.")


