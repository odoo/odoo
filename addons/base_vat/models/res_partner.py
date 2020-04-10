# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import string
import re
import stdnum

from odoo import api, models, tools, _
from odoo.tools.misc import ustr
from odoo.exceptions import ValidationError

_eu_country_vat = {
    'GR': 'EL'
}

_eu_country_vat_inverse = {v: k for k, v in _eu_country_vat.items()}

_ref_vat = {
    'al': 'ALJ91402501L',
    'ar': 'AR200-5536168-2 or 20055361682',
    'at': 'ATU12345675',
    'be': 'BE0477472701',
    'bg': 'BG1234567892',
    'ch': 'CHE-123.456.788 TVA or CH TVA 123456',  # Swiss by Yannick Vaucher @ Camptocamp
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
    'gb': 'GB123456782',
    'gr': 'GR12345670',
    'hu': 'HU12345676',
    'hr': 'HR01234567896',  # Croatia, contributed by Milan Tribuson
    'ie': 'IE1234567FA',
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
    'tr': 'TR1234567890 (VERGINO) or TR17291716060 (TCKIMLIKNO)'  # Levent Karakas @ Eska Yazilim A.S.
}


class ResPartner(models.Model):
    _inherit = 'res.partner'

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
        check_func = getattr(self, check_func_name, None) or getattr(stdnum.util.get_cc_module(country_code, 'vat'), 'is_valid', None)
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
        return stdnum.eu.vat.check_vies(vat)

    @api.model
    def vies_vat_check(self, country_code, vat_number):
        try:
            # Validate against  VAT Information Exchange System (VIES)
            # see also http://ec.europa.eu/taxation_customs/vies/
            return self._check_vies(country_code.upper() + vat_number)
        except Exception:
            # see http://ec.europa.eu/taxation_customs/vies/checkVatService.wsdl
            # Fault code may contain INVALID_INPUT, SERVICE_UNAVAILABLE, MS_UNAVAILABLE,
            # TIMEOUT or SERVER_BUSY. There is no way we can validate the input
            # with VIES if any of these arise, including the first one (it means invalid
            # country code or empty VAT number), so we fall back to the simple check.
            return self.simple_vat_check(country_code, vat_number)

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

    @api.constrains('vat', 'country_id')
    def check_vat(self):
        if self.env.context.get('company_id'):
            company = self.env['res.company'].browse(self.env.context['company_id'])
        else:
            company = self.env.company
        if company.vat_check_vies:
            # force full VIES online check
            check_func = self.vies_vat_check
        else:
            # quick and partial off-line checksum validation
            check_func = self.simple_vat_check
        for partner in self:
            if not partner.vat:
                continue
            #check with country code as prefix of the TIN
            vat_country, vat_number = self._split_vat(partner.vat)
            if not check_func(vat_country, vat_number):
                #if fails, check with country code from country
                country_code = partner.commercial_partner_id.country_id.code
                if country_code:
                    if not check_func(country_code.lower(), partner.vat):
                        msg = partner._construct_constraint_msg(country_code.lower())
                        raise ValidationError(msg)

    def _construct_constraint_msg(self, country_code):
        self.ensure_one()
        vat_no = "'CC##' (CC=Country Code, ##=VAT Number)"
        vat_no = _ref_vat.get(country_code) or vat_no
        if self.env.context.get('company_id'):
            company = self.env['res.company'].browse(self.env.context['company_id'])
        else:
            company = self.env.company
        if company.vat_check_vies:
            return '\n' + _('The VAT number [%s] for partner [%s] either failed the VIES VAT validation check or did not respect the expected format %s.') % (self.vat, self.name, vat_no)
        return '\n' + _('The VAT number [%s] for partner [%s] does not seem to be valid. \nNote: the expected format is %s') % (self.vat, self.name, vat_no)

    __check_vat_ch_re1 = re.compile(r'(MWST|TVA|IVA)[0-9]{6}$')
    __check_vat_ch_re2 = re.compile(r'E([0-9]{9}|-[0-9]{3}\.[0-9]{3}\.[0-9]{3})(MWST|TVA|IVA)$')

    def check_vat_ch(self, vat):
        '''
        Check Switzerland VAT number.
        '''
        # VAT number in Switzerland will change between 2011 and 2013
        # http://www.estv.admin.ch/mwst/themen/00154/00589/01107/index.html?lang=fr
        # Old format is "TVA 123456" we will admit the user has to enter ch before the number
        # Format will becomes such as "CHE-999.999.99C TVA"
        # Both old and new format will be accepted till end of 2013
        # Accepted format are: (spaces are ignored)
        #     CH TVA ######
        #     CH IVA ######
        #     CH MWST #######
        #
        #     CHE#########MWST
        #     CHE#########TVA
        #     CHE#########IVA
        #     CHE-###.###.### MWST
        #     CHE-###.###.### TVA
        #     CHE-###.###.### IVA
        #
        if self.__check_vat_ch_re1.match(vat):
            return True
        match = self.__check_vat_ch_re2.match(vat)
        if match:
            # For new TVA numbers, do a mod11 check
            num = [s for s in match.group(1) if s.isdigit()]        # get the digits only
            factor = (5, 4, 3, 2, 7, 6, 5, 4)
            csum = sum([int(num[i]) * factor[i] for i in range(8)])
            check = (11 - (csum % 11)) % 11
            return check == int(num[8])
        return False

    def _ie_check_char(self, vat):
        vat = vat.zfill(8)
        extra = 0
        if vat[7] not in ' W':
            if vat[7].isalpha():
                extra = 9 * (ord(vat[7]) - 64)
            else:
                # invalid
                return -1
        checksum = extra + sum((8-i) * int(x) for i, x in enumerate(vat[:7]))
        return 'WABCDEFGHIJKLMNOPQRSTUV'[checksum % 23]

    def check_vat_co(self, rut):
        '''
        Check Colombian RUT number.
        Method copied from vatnumber 1.2 lib https://code.google.com/archive/p/vatnumber/
        '''
        if len(rut) != 10:
            return False
        try:
            int(rut)
        except ValueError:
            return False
        nums = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]
        sum = 0
        for i in range(len(rut) - 2, -1, -1):
            sum += int(rut[i]) * nums[len(rut) - 2 - i]
        if sum % 11 > 1:
            return int(rut[-1]) == 11 - (sum % 11)
        else:
            return int(rut[-1]) == sum % 11

    def check_vat_ie(self, vat):
        """ Temporary Ireland VAT validation to support the new format
        introduced in January 2013 in Ireland, until upstream is fixed.
        TODO: remove when fixed upstream"""
        if len(vat) not in (8, 9) or not vat[2:7].isdigit():
            return False
        if len(vat) == 8:
            # Normalize pre-2013 numbers: final space or 'W' not significant
            vat += ' '
        if vat[:7].isdigit():
            return vat[7] == self._ie_check_char(vat[:7] + vat[8])
        elif vat[1] in (string.ascii_uppercase + '+*'):
            # Deprecated format
            # See http://www.revenue.ie/en/online/third-party-reporting/reporting-payment-details/faqs.html#section3
            return vat[7] == self._ie_check_char(vat[2:7] + vat[0] + vat[8])
        return False

    # Mexican VAT verification, contributed by Vauxoo
    # and Panos Christeas <p_christ@hol.gr>
    __check_vat_mx_re = re.compile(br"(?P<primeras>[A-Za-z\xd1\xf1&]{3,4})" \
                                   br"[ \-_]?" \
                                   br"(?P<ano>[0-9]{2})(?P<mes>[01][0-9])(?P<dia>[0-3][0-9])" \
                                   br"[ \-_]?" \
                                   br"(?P<code>[A-Za-z0-9&\xd1\xf1]{3})$")

    def check_vat_mx(self, vat):
        ''' Mexican VAT verification

        Verificar RFC México
        '''
        # we convert to 8-bit encoding, to help the regex parse only bytes
        vat = ustr(vat).encode('iso8859-1')
        m = self.__check_vat_mx_re.match(vat)
        if not m:
            #No valid format
            return False
        try:
            ano = int(m.group('ano'))
            if ano > 30:
                ano = 1900 + ano
            else:
                ano = 2000 + ano
            datetime.date(ano, int(m.group('mes')), int(m.group('dia')))
        except ValueError:
            return False

        # Valid format and valid date
        return True

    # Netherlands VAT verification
    __check_vat_nl_re = re.compile("(?:NL)?[0-9A-Z+*]{10}[0-9]{2}")

    def check_vat_nl(self, vat):
        """
        Temporary Netherlands VAT validation to support the new format introduced in January 2020,
        until upstream is fixed.

        Algorithm detail: http://kleineondernemer.nl/index.php/nieuw-btw-identificatienummer-vanaf-1-januari-2020-voor-eenmanszaken

        TODO: remove when fixed upstream
        """

        try:
            from stdnum.util import clean
            from stdnum.nl.bsn import checksum
        except ImportError:
            return True

        vat = clean(vat, ' -.').upper().strip()

        if not (len(vat) == 14):
            return False

        # Check the format
        match = self.__check_vat_nl_re.match(vat)
        if not match:
            return False

        # Match letters to integers
        char_to_int = {k: str(ord(k) - 55) for k in string.ascii_uppercase}
        char_to_int['+'] = '36'
        char_to_int['*'] = '37'

        # Remove the prefix
        vat = vat[2:]

        # 2 possible checks:
        # - For natural persons
        # - For non-natural persons and combinations of natural persons (company)

        # Natural person => mod97 full checksum
        check_val_natural = '2321'
        for x in vat:
            check_val_natural += x if x.isdigit() else char_to_int[x]
        if int(check_val_natural) % 97 == 1:
            return True

        # Company => weighted(9->2) mod11 on bsn
        vat = vat[:-3]
        if vat.isdigit() and checksum(vat) == 0:
            return True

        return False

    # Norway VAT validation, contributed by Rolv Råen (adEgo) <rora@adego.no>
    # Support for MVA suffix contributed by Bringsvor Consulting AS (bringsvor@bringsvor.com)
    def check_vat_no(self, vat):
        """
        Check Norway VAT number.See http://www.brreg.no/english/coordination/number.html
        """
        if len(vat) == 12 and vat.upper().endswith('MVA'):
            vat = vat[:-3] # Strictly speaking we should enforce the suffix MVA but...

        if len(vat) != 9:
            return False
        try:
            int(vat)
        except ValueError:
            return False

        sum = (3 * int(vat[0])) + (2 * int(vat[1])) + \
            (7 * int(vat[2])) + (6 * int(vat[3])) + \
            (5 * int(vat[4])) + (4 * int(vat[5])) + \
            (3 * int(vat[6])) + (2 * int(vat[7]))

        check = 11 - (sum % 11)
        if check == 11:
            check = 0
        if check == 10:
            # 10 is not a valid check digit for an organization number
            return False
        return check == int(vat[8])

    # Peruvian VAT validation, contributed by Vauxoo
    def check_vat_pe(self, vat):
        if len(vat) != 11 or not vat.isdigit():
            return False
        dig_check = 11 - (sum([int('5432765432'[f]) * int(vat[f]) for f in range(0, 10)]) % 11)
        if dig_check == 10:
            dig_check = 0
        elif dig_check == 11:
            dig_check = 1
        return int(vat[10]) == dig_check

    def check_vat_ru(self, vat):
        '''
        Check Russia VAT number.
        Method copied from vatnumber 1.2 lib https://code.google.com/archive/p/vatnumber/
        '''
        if len(vat) != 10 and len(vat) != 12:
            return False
        try:
            int(vat)
        except ValueError:
            return False

        if len(vat) == 10:
            check_sum = 2 * int(vat[0]) + 4 * int(vat[1]) + 10 * int(vat[2]) + \
                3 * int(vat[3]) + 5 * int(vat[4]) + 9 * int(vat[5]) + \
                4 * int(vat[6]) + 6 * int(vat[7]) + 8 * int(vat[8])
            check = check_sum % 11
            if check % 10 != int(vat[9]):
                return False
        else:
            check_sum1 = 7 * int(vat[0]) + 2 * int(vat[1]) + 4 * int(vat[2]) + \
                10 * int(vat[3]) + 3 * int(vat[4]) + 5 * int(vat[5]) + \
                9 * int(vat[6]) + 4 * int(vat[7]) + 6 * int(vat[8]) + \
                8 * int(vat[9])
            check = check_sum1 % 11

            if check != int(vat[10]):
                return False
            check_sum2 = 3 * int(vat[0]) + 7 * int(vat[1]) + 2 * int(vat[2]) + \
                4 * int(vat[3]) + 10 * int(vat[4]) + 3 * int(vat[5]) + \
                5 * int(vat[6]) + 9 * int(vat[7]) + 4 * int(vat[8]) + \
                6 * int(vat[9]) + 8 * int(vat[10])
            check = check_sum2 % 11
            if check != int(vat[11]):
                return False
        return True

    # VAT validation in Turkey, contributed by # Levent Karakas @ Eska Yazilim A.S.
    def check_vat_tr(self, vat):

        if not (10 <= len(vat) <= 11):
            return False
        try:
            int(vat)
        except ValueError:
            return False

        # check vat number (vergi no)
        if len(vat) == 10:
            sum = 0
            check = 0
            for f in range(0, 9):
                c1 = (int(vat[f]) + (9-f)) % 10
                c2 = (c1 * (2 ** (9-f))) % 9
                if (c1 != 0) and (c2 == 0):
                    c2 = 9
                sum += c2
            if sum % 10 == 0:
                check = 0
            else:
                check = 10 - (sum % 10)
            return int(vat[9]) == check

        # check personal id (tc kimlik no)
        if len(vat) == 11:
            c1a = 0
            c1b = 0
            c2 = 0
            for f in range(0, 9, 2):
                c1a += int(vat[f])
            for f in range(1, 9, 2):
                c1b += int(vat[f])
            c1 = ((7 * c1a) - c1b) % 10
            for f in range(0, 10):
                c2 += int(vat[f])
            c2 = c2 % 10
            return int(vat[9]) == c1 and int(vat[10]) == c2

        return False

    def check_vat_ua(self, vat):
        '''
        Check Ukraine VAT number.
        Method copied from vatnumber 1.2 lib https://code.google.com/archive/p/vatnumber/
        '''
        if len(vat) != 8:
            return False
        try:
            int(vat)
        except ValueError:
            return False
        return True

    def _fix_vat_number(self, vat, country_id):
        code = self.env['res.country'].browse(country_id).code if country_id else False
        vat_country, vat_number = self._split_vat(vat)
        if code and code.lower() != vat_country:
            return vat
        stdnum_vat_fix_func = getattr(stdnum.util.get_cc_module(vat_country, 'vat'), 'compact', None)
        #If any localization module need to define vat fix method for it's country then we give first priority to it.
        format_func_name = 'format_vat_' + vat_country
        format_func = getattr(self, format_func_name, None) or stdnum_vat_fix_func
        if format_func:
            vat_number = format_func(vat_number)
        return vat_country.upper() + vat_number

    @api.model
    def create(self, values):
        if values.get('vat'):
            country_id = values.get('country_id')
            values['vat'] = self._fix_vat_number(values['vat'], country_id)
        return super(ResPartner, self).create(values)

    def write(self, values):
        if values.get('vat') and len(self.mapped('country_id')) == 1:
            country_id = values.get('country_id', self.country_id.id)
            values['vat'] = self._fix_vat_number(values['vat'], country_id)
        return super(ResPartner, self).write(values)
