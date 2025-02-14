import datetime
import string
import re
import stdnum
from stdnum.eu.vat import check_vies
from stdnum.exceptions import InvalidComponent, InvalidChecksum, InvalidFormat
from stdnum.util import clean
from stdnum import luhn

import logging

from odoo import api, models, fields
from odoo.tools import _, zeep, LazyTranslate
from odoo.exceptions import ValidationError

_lt = LazyTranslate(__name__)
_logger = logging.getLogger(__name__)

_eu_country_vat = {
    'GR': 'EL'
}

_eu_country_vat_inverse = {v: k for k, v in _eu_country_vat.items()}

_ref_vat = {
    'al': 'ALJ91402501L',
    'ar': _lt('AR200-5536168-2 or 20055361682'),
    'at': 'ATU12345675',
    'au': '83 914 571 673',
    'be': 'BE0477472701',
    'bg': 'BG1234567892',
    'br': _lt('either 11 digits for CPF or 14 digits for CNPJ'),
    'cr': _lt('3101012009'),
    'ch': _lt('CHE-123.456.788 TVA or CHE-123.456.788 MWST or CHE-123.456.788 IVA'),  # Swiss by Yannick Vaucher @ Camptocamp
    'cl': 'CL76086428-5',
    'co': _lt('CO213123432-1 or CO213.123.432-1'),
    'cy': 'CY10259033P',
    'cz': 'CZ12345679',
    'de': _lt('DE123456788 or 12/345/67890'),
    'dk': 'DK12345674',
    'do': _lt('DO1-01-85004-3 or 101850043'),
    'ec': _lt('1792060346001 or 1792060346'),
    'ee': 'EE123456780',
    'es': 'ESA12345674',
    'fi': 'FI12345671',
    'fr': 'FR23334175221',
    'gb': _lt('GB123456782 or XI123456782'),
    'gr': 'EL123456783',
    'hu': _lt('HU12345676 or 12345678-1-11 or 8071592153'),
    'hr': 'HR01234567896',  # Croatia, contributed by Milan Tribuson
    'id': '1234567890123456',
    'ie': 'IE1234567FA',
    'il': _lt('XXXXXXXXX [9 digits] and it should respect the Luhn algorithm checksum'),
    'in': "12AAAAA1234AAZA",
    'is': 'IS062199',
    'it': 'IT12345670017',
    'kr': '123-45-67890 or 1234567890',
    'lt': 'LT123456715',
    'lu': 'LU12345613',
    'lv': 'LV41234567891',
    'ma': '12345678',
    'mc': 'FR53000004605',
    'mt': 'MT12345634',
    'mx': _lt('MXGODE561231GR8 or GODE561231GR8'),
    'nl': 'NL123456782B90',
    'no': 'NO123456785',
    'nz': _lt('49-098-576 or 49098576'),
    'pe': _lt('10XXXXXXXXY or 20XXXXXXXXY or 15XXXXXXXXY or 16XXXXXXXXY or 17XXXXXXXXY'),
    'ph': '123-456-789-123',
    'pl': 'PL1234567883',
    'pt': 'PT123456789',
    'ro': 'RO1234567897 or 8001011234567 or 9000123456789',
    'rs': 'RS101134702',
    'ru': 'RU123456789047',
    'se': 'SE123456789701',
    'si': 'SI12345679',
    'sk': 'SK2022749619',
    'sm': 'SM24165',
    'tr': _lt('17291716060 (NIN) or 1729171602 (VKN)'),
    'uy': _lt("Example: '219999830019' (format: 12 digits, all numbers, valid check digit)"),
    've': 'V-12345678-1, V123456781, V-12.345.678-1',
    'xi': 'XI123456782',
    'sa': _lt('310175397400003 [Fifteen digits, first and last digits should be "3"]')
}

_region_specific_vat_codes = {
    'xi',
    't',
}


class ResPartner(models.Model):
    _inherit = 'res.partner'

    vies_valid = fields.Boolean(
        string="Intra-Community Valid",
        compute='_compute_vies_valid', store=True, readonly=False,
        tracking=True,
        help='European VAT numbers are automatically checked on the VIES database.',
    )
    # Field representing whether vies_valid is relevant for selecting a fiscal position on this partner
    perform_vies_validation = fields.Boolean(compute='_compute_perform_vies_validation')
    # Technical field used to determine the VAT to check
    vies_vat_to_check = fields.Char(compute='_compute_vies_vat_to_check')

    def _split_vat(self, vat):
        '''
        Splits the VAT Number to get the country code in a first place and the code itself in a second place.
        This has to be done because some countries' code are one character long instead of two (i.e. "T" for Japan)
        '''
        if len(vat) > 1 and vat[1].isalpha():
            vat_country, vat_number = vat[:2].lower(), vat[2:].replace(' ', '')
        else:
            vat_country, vat_number = vat[:1].lower(), vat[1:].replace(' ', '')
        return vat_country, vat_number

    @api.model
    def simple_vat_check(self, country_code, vat_number):
        '''
        Check the VAT number depending of the country.
        http://sima-pc.com/nif.php
        '''
        if not country_code.encode().isalpha():
            return False
        check_func_name = 'check_vat_' + country_code
        check_func = getattr(self, check_func_name, None) or getattr(stdnum.util.get_cc_module(country_code, 'vat'), 'is_valid', None)
        if not check_func:
            # No VAT validation available, default to check that the country code exists
            country_code = _eu_country_vat_inverse.get(country_code, country_code)
            return bool(self.env['res.country'].search([('code', '=ilike', country_code)]))
        return check_func(vat_number)

    @api.depends('vat', 'country_id')
    def _compute_vies_vat_to_check(self):
        """ Retrieve the VAT number, if one such exists, to be used when checking against the VIES system """
        eu_country_codes = self.env.ref('base.europe').country_ids.mapped('code')
        for partner in self:
            # Skip checks when only one character is used. Some users like to put '/' or other as VAT to differentiate between
            # a partner for which they haven't yet input VAT, and one not subject to VAT
            if not partner.vat or len(partner.vat) == 1:
                partner.vies_vat_to_check = ''
                continue
            country_code, number = partner._split_vat(partner.vat)
            if not country_code.isalpha() and partner.country_id:
                country_code = partner.country_id.code
                number = partner.vat
            partner.vies_vat_to_check = (
                country_code.upper() in eu_country_codes or
                country_code.lower() in _region_specific_vat_codes
            ) and self._fix_vat_number(country_code + number, partner.country_id.id) or ''

    @api.depends_context('company')
    @api.depends('vies_vat_to_check')
    def _compute_perform_vies_validation(self):
        """ Determine whether to show VIES validity on the current VAT number """
        for partner in self:
            to_check = partner.vies_vat_to_check
            company_code = self.env.company.account_fiscal_country_id.code
            partner.perform_vies_validation = (
                to_check
                and not to_check[:2].upper() == company_code
                and self.env.company.vat_check_vies
            )

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
        # The context key 'no_vat_validation' allows you to store/set a VAT number without doing validations.
        # This is for API pushes from external platforms where you have no control over VAT numbers.
        if self.env.context.get('no_vat_validation'):
            return

        for partner in self:
            # Skip checks when only one character is used. Some users like to put '/' or other as VAT to differentiate between
            # A partner for which they didn't input VAT, and the one not subject to VAT
            if not partner.vat or len(partner.vat) == 1:
                continue
            country = partner.commercial_partner_id.country_id
            if self._run_vat_test(partner.vat, country, partner.is_company) is False:
                partner_label = _("partner [%s]", partner.name)
                msg = partner._build_vat_error_message(country and country.code.lower() or None, partner.vat, partner_label)
                raise ValidationError(msg)

    @api.depends('vies_vat_to_check')
    def _compute_vies_valid(self):
        """ Check the VAT number with VIES, if enabled."""
        if not self.env['res.company'].sudo().search_count([('vat_check_vies', '=', True)]):
            self.vies_valid = False
            return

        for partner in self:
            if not partner.vies_vat_to_check:
                partner.vies_valid = False
                continue
            if partner.parent_id and partner.parent_id.vies_vat_to_check == partner.vies_vat_to_check:
                partner.vies_valid = partner.parent_id.vies_valid
                continue
            try:
                _logger.info('Calling VIES service to check VAT for validation: %s', partner.vies_vat_to_check)
                vies_valid = check_vies(partner.vies_vat_to_check, timeout=10)
                partner.vies_valid = vies_valid['valid']
            except (OSError, InvalidComponent, zeep.exceptions.Fault) as e:
                if partner._origin.id:
                    msg = ""
                    if isinstance(e, OSError):
                        msg = _("Connection with the VIES server failed. The VAT number %s could not be validated.", partner.vies_vat_to_check)
                    elif isinstance(e, InvalidComponent):
                        msg = _("The VAT number %s could not be interpreted by the VIES server.", partner.vies_vat_to_check)
                    elif isinstance(e, zeep.exceptions.Fault):
                        msg = _('The request for VAT validation was not processed. VIES service has responded with the following error: %s', e.message)
                    partner._origin.message_post(body=msg)
                _logger.warning("The VAT number %s failed VIES check.", partner.vies_vat_to_check)
                partner.vies_valid = False

    @api.model
    def _run_vat_test(self, vat_number, default_country, partner_is_company=True):
        # OVERRIDE account
        check_result = None

        # First check with country code as prefix of the TIN
        vat_country_code, vat_number_split = self._split_vat(vat_number)

        if vat_country_code == 'eu' and default_country not in self.env.ref('base.europe').country_ids:
            # Foreign companies that trade with non-enterprises in the EU
            # may have a VATIN starting with "EU" instead of a country code.
            return True

        vat_has_legit_country_code = self.env['res.country'].search([('code', '=', vat_country_code.upper())], limit=1)
        if not vat_has_legit_country_code:
            vat_has_legit_country_code = vat_country_code.lower() in _region_specific_vat_codes
        if vat_has_legit_country_code:
            check_result = self.simple_vat_check(vat_country_code, vat_number_split)
            if check_result:
                return vat_country_code

        # If it fails, check with default_country (if it exists)
        if default_country:
            check_result = self.simple_vat_check(default_country.code.lower(), vat_number)
            if check_result:
                return default_country.code.lower()

        # We allow any number if it doesn't start with a country code and the partner has no country.
        # This is necessary to support an ORM limitation: setting vat and country_id together on a company
        # triggers two distinct write on res.partner, one for each field, both triggering this constraint.
        # If vat is set before country_id, the constraint must not break.
        return check_result

    @api.model
    def _build_vat_error_message(self, country_code, wrong_vat, record_label):
        # OVERRIDE account
        if self.env.context.get('company_id'):
            company = self.env['res.company'].browse(self.env.context['company_id'])
        else:
            company = self.env.company

        vat_label = _("VAT")
        if country_code and company.country_id and country_code == company.country_id.code.lower() and company.country_id.vat_label:
            vat_label = company.country_id.vat_label

        expected_format = _ref_vat.get(country_code, "'CC##' (CC=Country Code, ##=VAT Number)")

        # Catch use case where the record label is about the public user (name: False)
        if 'False' not in record_label:
            return '\n' + _(
                'The %(vat_label)s number [%(wrong_vat)s] for %(record_label)s does not seem to be valid. \nNote: the expected format is %(expected_format)s',
                vat_label=vat_label,
                wrong_vat=wrong_vat,
                record_label=record_label,
                expected_format=expected_format,
            )
        else:
            return '\n' + _(
                'The %(vat_label)s number [%(wrong_vat)s] does not seem to be valid. \nNote: the expected format is %(expected_format)s',
                vat_label=vat_label,
                wrong_vat=wrong_vat,
                expected_format=expected_format,
            )


    __check_vat_al_re = re.compile(r'^[JKLM][0-9]{8}[A-Z]$')

    def check_vat_al(self, vat):
        """Check Albania VAT number"""
        number = stdnum.util.get_cc_module('al', 'vat').compact(vat)

        if len(number) == 10 and self.__check_vat_al_re.match(number):
            return True
        return False

    __check_tin1_ro_natural_persons = re.compile(r'[1-9]\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{6}')
    __check_tin2_ro_natural_persons = re.compile(r'9000\d{9}')
    def check_vat_ro(self, vat):
        """
            Check Romanian VAT number that can be for example 'RO1234567897 or 'xyyzzaabbxxxx' or '9000xxxxxxxx'.
            - For xyyzzaabbxxxx, 'x' can be any number, 'y' is the two last digit of a year (in the range 00…99),
              'a' is a month, b is a day of the month, the number 8 and 9 are Country or district code
              (For those twos digits, we decided to let some flexibility  to avoid complexifying the regex and also
              for maintainability)
            - 9000xxxxxxxx, start with 9000 and then is filled by number In the range 0...9

            Also stdum also checks the CUI or CIF (Romanian company identifier). So a number like '123456897' will pass.
        """
        tin1 = self.__check_tin1_ro_natural_persons.match(vat)
        if tin1:
            return True
        tin2 = self.__check_tin1_ro_natural_persons.match(vat)
        if tin2:
            return True
        # Check the vat number
        return stdnum.util.get_cc_module('ro', 'vat').is_valid(vat)

    __check_tin_hu_individual_re = re.compile(r'^8\d{9}$')
    __check_tin_hu_companies_re = re.compile(r'^\d{8}-?[1-5]-?\d{2}$')
    __check_tin_hu_european_re = re.compile(r'^\d{8}$')

    def check_vat_hu(self, vat):
        """
            Check Hungary VAT number that can be for example 'HU12345676 or 'xxxxxxxx-y-zz' or '8xxxxxxxxy'
            - For xxxxxxxx-y-zz, 'x' can be any number, 'y' is a number between 1 and 5 depending on the person and the 'zz'
              is used for region code.
            - 8xxxxxxxxy, Tin number for individual, it has to start with an 8 and finish with the check digit
            - In case of EU format it will be the first 8 digits of the full VAT
        """
        companies = self.__check_tin_hu_companies_re.match(vat)
        if companies:
            return True
        individual = self.__check_tin_hu_individual_re.match(vat)
        if individual:
            return True
        european = self.__check_tin_hu_european_re.match(vat)
        if european:
            return True
        # Check the vat number
        return stdnum.util.get_cc_module('hu', 'vat').is_valid(vat)

    __check_vat_ch_re = re.compile(r'E([0-9]{9}|-[0-9]{3}\.[0-9]{3}\.[0-9]{3})(MWST|TVA|IVA)$')

    def check_vat_ch(self, vat):
        '''
        Check Switzerland VAT number.
        '''
        # A new VAT number format in Switzerland has been introduced between 2011 and 2013
        # https://www.estv.admin.ch/estv/fr/home/mehrwertsteuer/fachinformationen/steuerpflicht/unternehmens-identifikationsnummer--uid-.html
        # The old format "TVA 123456" is not valid since 2014
        # Accepted format are: (spaces are ignored)
        #     CHE#########MWST
        #     CHE#########TVA
        #     CHE#########IVA
        #     CHE-###.###.### MWST
        #     CHE-###.###.### TVA
        #     CHE-###.###.### IVA
        #
        # /!\ The english abbreviation VAT is not valid /!\

        match = self.__check_vat_ch_re.match(vat)

        if match:
            # For new TVA numbers, the last digit is a MOD11 checksum digit build with weighting pattern: 5,4,3,2,7,6,5,4
            num = [s for s in match.group(1) if s.isdigit()]        # get the digits only
            factor = (5, 4, 3, 2, 7, 6, 5, 4)
            csum = sum([int(num[i]) * factor[i] for i in range(8)])
            check = (11 - (csum % 11)) % 11
            return check == int(num[8])
        return False


    def is_valid_ruc_ec(self, vat):
        if len(vat) in (10, 13) and vat.isdecimal():
            return True
        return False

    def check_vat_ec(self, vat):
        vat = clean(vat, ' -.').upper().strip()
        return self.is_valid_ruc_ec(vat)

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

    # TODO: remove in master
    def check_vat_ie(self, vat):
        return stdnum.util.get_cc_module('ie', 'vat').is_valid(vat)

    # Mexican VAT verification, contributed by Vauxoo
    # and Panos Christeas <p_christ@hol.gr>
    __check_vat_mx_re = re.compile(r"(?P<primeras>[A-Za-z\xd1\xf1&]{3,4})"
                                   r"[ \-_]?"
                                   r"(?P<ano>[0-9]{2})(?P<mes>[01][0-9])(?P<dia>[0-3][0-9])"
                                   r"[ \-_]?"
                                   r"(?P<code>[A-Za-z0-9&\xd1\xf1]{3})")

    def check_vat_mx(self, vat):
        ''' Mexican VAT verification

        Verificar RFC México
        '''
        m = self.__check_vat_mx_re.fullmatch(vat)
        if not m:
            #No valid format
            return False
        ano = int(m['ano'])
        if ano > 30:
            ano = 1900 + ano
        else:
            ano = 2000 + ano
        try:
            datetime.date(ano, int(m['mes']), int(m['dia']))
        except ValueError:
            return False

        # Valid format and valid date
        return True

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

    # Philippines TIN (+ branch code) validation
    __check_vat_ph_re = re.compile(r"\d{3}-\d{3}-\d{3}(-\d{3,5})?$")

    def check_vat_ph(self, vat):
        return len(vat) >= 11 and len(vat) <= 17 and self.__check_vat_ph_re.match(vat)

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

    # VAT validation in Turkey
    def check_vat_tr(self, vat):
        return stdnum.util.get_cc_module('tr', 'tckimlik').is_valid(vat) or stdnum.util.get_cc_module('tr', 'vkn').is_valid(vat)

    __check_vat_sa_re = re.compile(r"^3[0-9]{13}3$")

    # Saudi Arabia TIN validation
    def check_vat_sa(self, vat):
        """
            Check company VAT TIN according to ZATCA specifications: The VAT number should start and begin with a '3'
            and be 15 digits long
        """
        return self.__check_vat_sa_re.match(vat) or False

    def check_vat_ua(self, vat):
        res = []
        for partner in self:
            if partner.commercial_partner_id.country_id.code == 'MX':
                if len(vat) == 10:
                    res.append(True)
                else:
                    res.append(False)
            elif partner.commercial_partner_id.is_company:
                if len(vat) == 12:
                    res.append(True)
                else:
                    res.append(False)
            else:
                if len(vat) == 10 or len(vat) == 9:
                    res.append(True)
                else:
                    res.append(False)
        return all(res)

    def check_vat_uy(self, vat):
        """ Taken from python-stdnum's master branch, as the release doesn't handle RUT numbers starting with 22.
        origin https://github.com/arthurdejong/python-stdnum/blob/master/stdnum/uy/rut.py
        FIXME Can be removed when python-stdnum does a new release. """

        def compact(number):
            """Convert the number to its minimal representation."""
            number = clean(number, ' -').upper().strip()
            if number.startswith('UY'):
                return number[2:]
            return number

        def calc_check_digit(number):
            """Calculate the check digit."""
            weights = (4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
            total = sum(int(n) * w for w, n in zip(weights, number))
            return str(-total % 11)

        vat = compact(vat)

        return (
            vat.isdigit()  # InvalidFormat
            and len(vat) == 12  # InvalidLength
            and '01' <= vat[:2] <= '22'  # InvalidComponent
            and vat[2:8] != '000000'
            and vat[8:11] == '001'
            and vat[-1] == calc_check_digit(vat)  # Invalid Check Digit
        )

    def check_vat_ve(self, vat):
        # https://tin-check.com/en/venezuela/
        # https://techdocs.broadcom.com/us/en/symantec-security-software/information-security/data-loss-prevention/15-7/About-content-packs/What-s-included-in-Content-Pack-2021-02/Updated-data-identifiers-in-Content-Pack-2021-02/venezuela-national-identification-number-v115451096-d327e108002-CP2021-02.html
        # Sources last visited on 2022-12-09

        # VAT format: (kind - 1 letter)(identifier number - 8-digit number)(check digit - 1 digit)
        vat_regex = re.compile(r"""
            ([vecjpg])                          # group 1 - kind
            (
                (?P<optional_1>-)?                      # optional '-' (1)
                [0-9]{2}
                (?(optional_1)(?P<optional_2>[.])?)     # optional '.' (2) only if (1)
                [0-9]{3}
                (?(optional_2)[.])                      # mandatory '.' if (2)
                [0-9]{3}
                (?(optional_1)-)                        # mandatory '-' if (1)
            )                                   # group 2 - identifier number
            ([0-9]{1})                          # group X - check digit
        """, re.VERBOSE | re.IGNORECASE)

        matches = re.fullmatch(vat_regex, vat)
        if not matches:
            return False

        kind, identifier_number, *_, check_digit = matches.groups()
        kind = kind.lower()
        identifier_number = identifier_number.replace("-", "").replace(".", "")
        check_digit = int(check_digit)

        if kind == 'v':                   # Venezuela citizenship
            kind_digit = 1
        elif kind == 'e':                 # Foreigner
            kind_digit = 2
        elif kind == 'c' or kind == 'j':  # Township/Communal Council or Legal entity
            kind_digit = 3
        elif kind == 'p':                 # Passport
            kind_digit = 4
        else:                             # Government ('g')
            kind_digit = 5

        # === Checksum validation ===
        multipliers = [3, 2, 7, 6, 5, 4, 3, 2]
        checksum = kind_digit * 4
        checksum += sum(map(lambda n, m: int(n) * m, identifier_number, multipliers))

        checksum_digit = 11 - checksum % 11
        if checksum_digit > 9:
            checksum_digit = 0

        return check_digit == checksum_digit

    def check_vat_in(self, vat):
        #reference from https://www.gstzen.in/a/format-of-a-gst-number-gstin.html
        if vat and len(vat) == 15:
            all_gstin_re = [
                r'[0-9]{2}[a-zA-Z]{5}[0-9]{4}[a-zA-Z]{1}[1-9A-Za-z]{1}[Zz1-9A-Ja-j]{1}[0-9a-zA-Z]{1}', # Normal, Composite, Casual GSTIN
                r'[0-9]{4}[A-Z]{3}[0-9]{5}[UO]{1}[N][A-Z0-9]{1}', #UN/ON Body GSTIN
                r'[0-9]{4}[a-zA-Z]{3}[0-9]{5}[N][R][0-9a-zA-Z]{1}', #NRI GSTIN
                r'[0-9]{2}[a-zA-Z]{4}[a-zA-Z0-9]{1}[0-9]{4}[a-zA-Z]{1}[1-9A-Za-z]{1}[DK]{1}[0-9a-zA-Z]{1}', #TDS GSTIN
                r'[0-9]{2}[a-zA-Z]{5}[0-9]{4}[a-zA-Z]{1}[1-9A-Za-z]{1}[C]{1}[0-9a-zA-Z]{1}' #TCS GSTIN
            ]
            return any(re.compile(rx).match(vat) for rx in all_gstin_re)
        return False

    def check_vat_t(self, vat):
        if self.country_id.code == 'JP':
            return self.simple_vat_check('jp', vat)

    def check_vat_br(self, vat):
        is_cpf_valid = stdnum.get_cc_module('br', 'cpf').is_valid
        is_cnpj_valid = stdnum.get_cc_module('br', 'cnpj').is_valid
        return is_cpf_valid(vat) or is_cnpj_valid(vat)

    __check_vat_cr_re = re.compile(r'^(?:[1-9]\d{8}|\d{10}|[1-9]\d{10,11})$')

    def check_vat_cr(self, vat):
        # CÉDULA FÍSICA: 9 digits
        # CÉDULA JURÍDICA: 10 digits
        # CÉDULA DIMEX: 11 or 12 digits
        # CÉDULA NITE: 10 digits

        return self.__check_vat_cr_re.match(vat) or False

    def format_vat_eu(self, vat):
        # Foreign companies that trade with non-enterprises in the EU
        # may have a VATIN starting with "EU" instead of a country code.
        return vat

    def format_vat_ch(self, vat):
        stdnum_vat_format = getattr(stdnum.util.get_cc_module('ch', 'vat'), 'format', None)
        return stdnum_vat_format('CH' + vat)[2:] if stdnum_vat_format else vat

    def check_vat_id(self, vat):
        """ Temporary Indonesian VAT validation to support the new format
        introduced in January 2024."""
        vat = clean(vat, ' -.').strip()

        if len(vat) not in (15, 16) or not vat.isdecimal():
            return False

        # VAT could be 15 (old numbers) or 16 digits. If there are 15 digits long, the 10th digit is a luhn checksum
        # In some cases, the 15 digits can be transformed in a 16-digit by adding a 0 in front. In such case, we
        # we can verify the luhn checksum like for the 15 digits by removing the 0. 
        # However, for newly created VAT 16-digits VAT number, there is no checksum.
        if (len(vat) == 16 and vat[0] != '0'):
            return True

        try:
            luhn.validate(vat[0:9] if len(vat) == 15 else vat[1:10])
        except (InvalidFormat, InvalidChecksum):
            return False

        return True

    def check_vat_de(self, vat):
        is_valid_vat = stdnum.util.get_cc_module("de", "vat").is_valid
        is_valid_stnr = stdnum.util.get_cc_module("de", "stnr").is_valid
        return is_valid_vat(vat) or is_valid_stnr(vat)

    def check_vat_il(self, vat):
        check_func = stdnum.util.get_cc_module('il', 'idnr').is_valid
        return check_func(vat)

    def check_vat_ma(self, vat):
        return vat.isdigit() and len(vat) == 8

    def format_vat_sm(self, vat):
        stdnum_vat_format = stdnum.util.get_cc_module('sm', 'vat').compact
        return stdnum_vat_format('SM' + vat)[2:]

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
    def _convert_hu_local_to_eu_vat(self, local_vat):
        if self.__check_tin_hu_companies_re.match(local_vat):
            return f'HU{local_vat[:8]}'
        return False

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get('vat'):
                country_id = values.get('country_id')
                values['vat'] = self._fix_vat_number(values['vat'], country_id)
        res = super().create(vals_list)
        if self.env.context.get('import_file'):
            res.env.remove_to_compute(self._fields['vies_valid'], res)
        return res

    def write(self, values):
        if values.get('vat') and len(self.mapped('country_id')) == 1:
            country_id = values.get('country_id', self.country_id.id)
            values['vat'] = self._fix_vat_number(values['vat'], country_id)
        res = super().write(values)
        if self.env.context.get('import_file'):
            self.env.remove_to_compute(self._fields['vies_valid'], self)
        return res
