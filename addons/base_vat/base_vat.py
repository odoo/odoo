# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2011 OpenERP SA (<http://openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging
import string
import datetime
import re
_logger = logging.getLogger(__name__)

try:
    import vatnumber
except ImportError:
    _logger.warning("VAT validation partially unavailable because the `vatnumber` Python library cannot be found. "
                                          "Install it to support more countries, for example with `easy_install vatnumber`.")
    vatnumber = None

from osv import osv, fields
from tools.misc import ustr
from tools.translate import _

_ref_vat = {
    'at': 'ATU12345675',
    'be': 'BE0477472701',
    'bg': 'BG1234567892',
    'ch': 'CHE-123.456.788 TVA or CH TVA 123456', #Swiss by Yannick Vaucher @ Camptocamp
    'cy': 'CY12345678F',
    'cz': 'CZ12345679',
    'de': 'DE123456788',
    'dk': 'DK12345674',
    'ee': 'EE123456780',
    'el': 'EL12345670',
    'es': 'ESA12345674',
    'fi': 'FI12345671',
    'fr': 'FR32123456789',
    'gb': 'GB123456782',
    'gr': 'GR12345670',
    'hu': 'HU12345676',
    'hr': 'HR01234567896', # Croatia, contributed by Milan Tribuson 
    'ie': 'IE1234567T',
    'it': 'IT12345670017',
    'lt': 'LT123456715',
    'lu': 'LU12345613',
    'lv': 'LV41234567891',
    'mt': 'MT12345634',
    'mx': 'MXABC123456T1B',
    'nl': 'NL123456782B90',
    'no': 'NO123456785',
    'pl': 'PL1234567883',
    'pt': 'PT123456789',
    'ro': 'RO1234567897',
    'se': 'SE123456789701',
    'si': 'SI12345679',
    'sk': 'SK0012345675',
}

class res_partner(osv.osv):
    _inherit = 'res.partner'

    def _split_vat(self, vat):
        vat_country, vat_number = vat[:2].lower(), vat[2:].replace(' ', '')
        return vat_country, vat_number

    def simple_vat_check(self, cr, uid, country_code, vat_number, context=None):
        '''
        Check the VAT number depending of the country.
        http://sima-pc.com/nif.php
        '''
        check_func_name = 'check_vat_' + country_code
        check_func = getattr(self, check_func_name, None) or \
                        getattr(vatnumber, check_func_name, None)
        if not check_func:
            # No VAT validation available, default to check that the country code exists
            res_country = self.pool.get('res.country')
            return bool(res_country.search(cr, uid, [('code', '=ilike', country_code)], context=context))
        return check_func(vat_number)

    def vies_vat_check(self, cr, uid, country_code, vat_number, context=None):
        try:
            # Validate against  VAT Information Exchange System (VIES)
            # see also http://ec.europa.eu/taxation_customs/vies/
            return vatnumber.check_vies(country_code.upper()+vat_number)
        except Exception:
            # see http://ec.europa.eu/taxation_customs/vies/checkVatService.wsdl
            # Fault code may contain INVALID_INPUT, SERVICE_UNAVAILABLE, MS_UNAVAILABLE,
            # TIMEOUT or SERVER_BUSY. There is no way we can validate the input
            # with VIES if any of these arise, including the first one (it means invalid
            # country code or empty VAT number), so we fall back to the simple check.
            return self.simple_vat_check(cr, uid, country_code, vat_number, context=context)

    def button_check_vat(self, cr, uid, ids, context=None):
        if not self.check_vat(cr, uid, ids, context=context):
            msg = self._construct_constraint_msg(cr, uid, ids, context=context)
            raise osv.except_osv(_('Error!'), msg)

    def check_vat(self, cr, uid, ids, context=None):
        user_company = self.pool.get('res.users').browse(cr, uid, uid).company_id
        if user_company.vat_check_vies:
            # force full VIES online check
            check_func = self.vies_vat_check
        else:
            # quick and partial off-line checksum validation
            check_func = self.simple_vat_check
        for partner in self.browse(cr, uid, ids, context=context):
            if not partner.vat:
                continue
            vat_country, vat_number = self._split_vat(partner.vat)
            if not check_func(cr, uid, vat_country, vat_number, context=context):
                return False
        return True

    def vat_change(self, cr, uid, ids, value, context=None):
        return {'value': {'vat_subjected': bool(value)}}

    _columns = {
        'vat_subjected': fields.boolean('VAT Legal Statement', help="Check this box if the partner is subjected to the VAT. It will be used for the VAT legal statement.")
    }

    def _construct_constraint_msg(self, cr, uid, ids, context=None):
        def default_vat_check(cn, vn):
            # by default, a VAT number is valid if:
            #  it starts with 2 letters
            #  has more than 3 characters
            return cn[0] in string.ascii_lowercase and cn[1] in string.ascii_lowercase
        vat_country, vat_number = self._split_vat(self.browse(cr, uid, ids)[0].vat)
        vat_no = "'CC##' (CC=Country Code, ##=VAT Number)"
        if default_vat_check(vat_country, vat_number):
            vat_no = _ref_vat[vat_country] if vat_country in _ref_vat else vat_no
        return '\n' + _('This VAT number does not seem to be valid.\nNote: the expected format is %s') % vat_no

    _constraints = [(check_vat, _construct_constraint_msg, ["vat"])]


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
            num = filter(lambda s: s.isdigit(), match.group(1))        # get the digits only
            factor = (5,4,3,2,7,6,5,4)
            csum = sum([int(num[i]) * factor[i] for i in range(8)])
            check = 11 - (csum % 11)
            return check == int(num[8])
        return False


    # Mexican VAT verification, contributed by <moylop260@hotmail.com>
    # and Panos Christeas <p_christ@hol.gr>
    __check_vat_mx_re = re.compile(r"(?P<primeras>[A-Za-z\xd1\xf1&]{3,4})" \
                                    r"[ \-_]?" \
                                    r"(?P<ano>[0-9]{2})(?P<mes>[01][0-9])(?P<dia>[0-3][0-9])" \
                                    r"[ \-_]?" \
                                    r"(?P<code>[A-Za-z0-9&\xd1\xf1]{3})$")
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

        #Valid format and valid date
        return True


    # Norway VAT validation, contributed by Rolv Råen (adEgo) <rora@adego.no>
    def check_vat_no(self, vat):
        '''
        Check Norway VAT number.See http://www.brreg.no/english/coordination/number.html
        '''
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

        check = 11 -(sum % 11)
        if check == 11:
            check = 0
        if check == 10:
            # 10 is not a valid check digit for an organization number
            return False
        return check == int(vat[8])

res_partner()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
