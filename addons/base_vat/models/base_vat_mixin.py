# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import stdnum
from stdnum.eu.vat import check_vies

import logging

from odoo import api, models, fields, tools, _
from odoo.tools.misc import ustr
from odoo.exceptions import ValidationError


_logger = logging.getLogger(__name__)

_eu_country_vat = {
    'GR': 'EL'
}

_eu_country_vat_inverse = {v: k for k, v in _eu_country_vat.items()}

_ref_vat = {
    'al': 'ALJ91402501L',
    'ar': 'AR200-5536168-2 or 20055361682',
    'at': 'ATU12345675',
    'au': '83 914 571 673',
    'be': 'BE0477472701',
    'bg': 'BG1234567892',
    'ch': 'CHE-123.456.788 TVA or CHE-123.456.788 MWST or CHE-123.456.788 IVA',  # Swiss by Yannick Vaucher @ Camptocamp
    'cl': 'CL76086428-5',
    'co': 'CO213123432-1 or CO213.123.432-1',
    'cy': 'CY10259033P',
    'cz': 'CZ12345679',
    'de': 'DE123456788',
    'dk': 'DK12345674',
    'do': 'DO1-01-85004-3 or 101850043',
    'ec': 'EC1792060346-001',
    'ee': 'EE123456780',
    'el': 'EL12345670',
    'es': 'ESA12345674',
    'fi': 'FI12345671',
    'fr': 'FR23334175221',
    'gb': 'GB123456782 or XI123456782',
    'gr': 'GR12345670',
    'hu': 'HU12345676',
    'hr': 'HR01234567896',  # Croatia, contributed by Milan Tribuson
    'ie': 'IE1234567FA',
    'in': "12AAAAA1234AAZA",
    'is': 'IS062199',
    'it': 'IT12345670017',
    'lt': 'LT123456715',
    'lu': 'LU12345613',
    'lv': 'LV41234567891',
    'mc': 'FR53000004605',
    'mt': 'MT12345634',
    'mx': 'MXGODE561231GR8 or GODE561231GR8',
    'nl': 'NL123456782B90',
    'no': 'NO123456785',
    'pe': '10XXXXXXXXY or 20XXXXXXXXY or 15XXXXXXXXY or 16XXXXXXXXY or 17XXXXXXXXY',
    'pl': 'PL1234567883',
    'pt': 'PT123456789',
    'ro': 'RO1234567897',
    'rs': 'RS101134702',
    'ru': 'RU123456789047',
    'se': 'SE123456789701',
    'si': 'SI12345679',
    'sk': 'SK2022749619',
    'sm': 'SM24165',
    'tr': 'TR1234567890 (VERGINO) or TR17291716060 (TCKIMLIKNO)',  # Levent Karakas @ Eska Yazilim A.S.
    'xi': 'XI123456782',
}

_region_specific_vat_codes = {
    'xi',
}


class ViesFail(stdnum.exceptions.ValidationError):
    pass


class VatMixin(models.AbstractModel):
    _name = 'base.vat.mixin'
    _description = 'VAT and similar identifier checker'

    _base_vat_vat_field = 'vat'
    _base_vat_country_field = 'country_id'

    vat_error = fields.Char(compute='_compute_base_vat')
    vat_country_id = fields.Many2one('res.country', compute='_compute_base_vat')
    vat_label = fields.Char(compute='_compute_base_vat')

    @api.depends(lambda self: (self._base_vat_vat_field, self._base_vat_country_field))
    def _compute_base_vat(self):
        for record in self:
            record.vat_error = False
            record.vat_country_id = False
            record.vat_label = (
                record[record._base_vat_country_field].vat_label
                or ('company_id' in record._fields and record.company_id.country_id.vat_label)
                or self.env.company.country_id.vat_label
                or _('VAT')
            )
            if record[self._base_vat_vat_field]:
                try:
                    country_code = record._run_vat_test()
                    if country_code and re.match('^[a-zA-Z]{2}$', country_code):
                        record.vat_country_id = self.env['res.country'].search([('code', '=', country_code.upper())])
                        if record.vat_country_id.vat_label:
                            record.vat_label = record.vat_country_id.vat_label
                except stdnum.exceptions.InvalidLength:
                    record.vat_error = _("The number has an invalid length.")
                except stdnum.exceptions.InvalidFormat:
                    record.vat_error = _("The number has an invalid format.")
                except stdnum.exceptions.InvalidChecksum:
                    record.vat_error = _("The number's checksum or check digit is invalid.")
                except stdnum.exceptions.InvalidComponent:
                    record.vat_error = _("One of the parts of the number are invalid or unknown.")
                except ViesFail:
                    record.vat_error = _("The VAT number does not exist on VIES.")

    @api.constrains(lambda self: (self._base_vat_vat_field, self._base_vat_country_field))
    def _constrains_vat_country(self):
        for record in self:
            if record.vat_error:
                raise ValidationError(_(
                    "The VAT number [%(wrong_vat)s] for %(description)s #%(id)s is not valid.\n"
                    "%(hint)s\n\n"
                    "Hint: the expected format is %(expected_format)s",
                    wrong_vat=self[record._base_vat_vat_field],
                    description=record._description,
                    id=record.id,
                    expected_format=_ref_vat.get(
                        (record[record._base_vat_country_field].code or "").lower(),
                        "'CC##' (CC=Country Code, ##=VAT Number)"
                    ),
                    hint=record.vat_error,
                ))

    def _sanitize_vals_base_vat(self, vals):
        if vals.get(self._base_vat_vat_field):
            vals[self._base_vat_vat_field] = self._fix_vat_number(
                vals[self._base_vat_vat_field],
                vals.get(self._base_vat_country_field, self[self._base_vat_country_field].id),
            )
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        return super().create([self._sanitize_vals_base_vat(vals) for vals in vals_list])

    def write(self, values):
        return super().write(self._sanitize_vals_base_vat(values))

    def _split_vat(self, vat):
        vat_country, vat_number = vat[:2].lower(), vat[2:].replace(' ', '')
        return vat_country, vat_number

    @api.model
    def simple_vat_check(self, country_code, vat_number):
        '''
        Check the VAT number depending of the country.
        http://sima-pc.com/nif.php
        '''
        if not ustr(country_code).encode('utf-8').isalpha():
            return False
        check_func_name = 'check_vat_' + country_code
        check_func = getattr(self, check_func_name, None) or getattr(stdnum.util.get_cc_module(country_code, 'vat'), 'validate', None)
        if not check_func:
            # No VAT validation available, default to check that the country code exists
            if country_code.upper() == 'EU':
                # Foreign companies that trade with non-enterprises in the EU
                # may have a VATIN starting with "EU" instead of a country code.
                return True
            country_code = _eu_country_vat_inverse.get(country_code, country_code)
            return bool(self.env['res.country'].search([('code', '=ilike', country_code)]))
        return check_func(vat_number)

    @api.model
    @tools.ormcache('vat')
    def _check_vies(self, vat):
        # Store the VIES result in the cache. In case an exception is raised during the request
        # (e.g. service unavailable), the fallback on simple_vat_check is not kept in cache.
        return check_vies(vat)

    @api.model
    def vies_vat_check(self, country_code, vat_number):
        try:
            # Validate against  VAT Information Exchange System (VIES)
            # see also http://ec.europa.eu/taxation_customs/vies/
            vies_result = self._check_vies(country_code.upper() + vat_number)
            if not vies_result['valid']:
                raise ViesFail
        except stdnum.exceptions.ValidationError:
            raise
        except Exception:
            # see http://ec.europa.eu/taxation_customs/vies/checkVatService.wsdl
            # Fault code may contain INVALID_INPUT, SERVICE_UNAVAILABLE, MS_UNAVAILABLE,
            # TIMEOUT or SERVER_BUSY. There is no way we can validate the input
            # with VIES if any of these arise, including the first one (it means invalid
            # country code or empty VAT number), so we fall back to the simple check.
            _logger.exception("Failed VIES VAT check for partner#%s and number %s.", self.id, vat_number)
            self.simple_vat_check(country_code, vat_number)

    @api.model
    def fix_eu_vat_number(self, country_id, vat):
        europe = self.env.ref('base.europe')
        country = self.env["res.country"].browse(country_id)
        if not europe:
            europe = self.env["res.country.group"].search([('name', '=', 'Europe')], limit=1)
        if europe and country and country.id in europe.country_ids.ids:
            vat = re.sub('[^A-Za-z0-9]', '', vat).upper()
            country_code = _eu_country_vat.get(country.code, country.code).upper()
            if vat[:2] != country_code:
                vat = country_code + vat
        return vat

    def _fix_vat_number(self, vat, country_id):
        code = self.env['res.country'].browse(country_id).code
        vat_country, _vat_number = self._split_vat(vat)
        if code and code.lower() != vat_country:
            return vat
        #If any localization module need to define vat fix method for it's country then we give first priority to it.
        custom_format = getattr(self, 'format_vat_' + vat_country, None)
        default_format = getattr(stdnum.util.get_cc_module(vat_country, 'vat'), 'format', None)
        format_func = custom_format or default_format
        if format_func:
            return format_func(vat)
        return vat

    def _run_vat_test(self):
        """ Checks a VAT number, either syntactically or using VIES, depending
        on the active company's configuration.
        A first check is made by using the first two characters of the VAT as
        the country code. It it fails, a second one is made using default_country instead.

        :return: The country code (in lower case) of the country the VAT number
                 was validated for, if it was validated. False if it could not be validated
                 against the provided or guessed country. None if no country was available
                 for the check, and no conclusion could be made with certainty.
        """
        # Get company
        if 'company_id' in self._fields:
            company = self.company_id
        elif self.env.context.get('company_id'):
            company = self.env['res.company'].browse(self.env.context['company_id'])
        else:
            company = self.env.company

        # Get check function: either simple syntactic check or call to VIES service
        eu_countries = self.env.ref('base.europe').country_ids
        if company.vat_check_vies and self[self._base_vat_country_field] in eu_countries:
            check_func = self.vies_vat_check
        else:
            check_func = self.simple_vat_check
        # First check with country code as prefix of the TIN
        vat_country_code, vat_number_split = self._split_vat(self[self._base_vat_vat_field])
        vat_has_legit_country_code = self.env['res.country'].search([('code', '=', vat_country_code.upper())])
        if not vat_has_legit_country_code:
            vat_has_legit_country_code = vat_country_code.lower() in _region_specific_vat_codes
        try:
            if self[self._base_vat_country_field] and not vat_has_legit_country_code:
                raise stdnum.exceptions.InvalidFormat
            check_func(vat_country_code, vat_number_split)
            return vat_country_code
        except stdnum.exceptions.ValidationError:
            # If it fails, check with default_country (if it exists)
            if self[self._base_vat_country_field]:
                check_func(self[self._base_vat_country_field].code.lower(), self[self._base_vat_vat_field])
                return self[self._base_vat_country_field].code.lower()
            raise
