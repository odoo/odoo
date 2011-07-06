# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    Copyright (C) 2008-2009 B2CK, Cedric Krier, Bertrand Chenal (the methods "check_vat_[a-z]{2}"
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

import string
import datetime
import vatnumber
import re

from osv import osv, fields
from tools.misc import ustr
from tools.translate import _

_ref_vat = {
    'be': 'BE0477472701', 'at': 'ATU12345675',
    'bg': 'BG1234567892', 'cy': 'CY12345678F',
    'cz': 'CZ12345679', 'de': 'DE123456788',
    'dk': 'DK12345674', 'ee': 'EE123456780',
    'es': 'ESA12345674', 'fi': 'FI12345671',
    'fr': 'FR32123456789', 'gb': 'GB123456782',
    'gr': 'GR12345670', 'hu': 'HU12345676',
    'ie': 'IE1234567T', 'it': 'IT12345670017',
    'lt': 'LT123456715', 'lu': 'LU12345613',
    'lv': 'LV41234567891', 'mt': 'MT12345634',
    'nl': 'NL123456782B90', 'pl': 'PL1234567883',
    'pt': 'PT123456789', 'ro': 'RO1234567897',
    'se': 'SE123456789701', 'si': 'SI12345679',
    'sk': 'SK0012345675', 'el': 'EL12345670',
    'mx': 'MXABCD831230T1B',
}

class res_partner(osv.osv):
    _inherit = 'res.partner'

    def _split_vat(self, vat):
        vat_country, vat_number = vat[:2].lower(), vat[2:].replace(' ', '')
        return vat_country, vat_number

    def check_vat(self, cr, uid, ids, context=None):
        '''
        Check the VAT number depending of the country.
        http://sima-pc.com/nif.php
        '''
        country_obj = self.pool.get('res.country')
        for partner in self.browse(cr, uid, ids, context=context):
            if not partner.vat:
                continue
            vat_country, vat_number = self._split_vat(partner.vat)
            if not hasattr(self, 'check_vat_' + vat_country) and not hasattr(vatnumber, 'check_vat_' + vat_country):
                #We didn't find the validation method for the country code. If that country code can be found in openerp, this means that it is a valid country code
                #and we simply didn't have implemented that function. In that case we continue.
                if country_obj.search(cr, uid, [('code', 'ilike', vat_country)], context=context):
                    continue
                #Otherwise, it means that the country code isn't valid and we return False.
                return False
            check = getattr(self, 'check_vat_' + vat_country, False) or getattr(vatnumber, 'check_vat_' + vat_country, False)
            if not check(vat_number):
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
        if default_vat_check(vat_country, vat_number):
            vat_no = vat_country in _ref_vat and _ref_vat[vat_country] or 'Country Code + Vat Number'
            return _('The Vat does not seems to be correct. You should have entered something like this %s'), (vat_no)
        return _('The VAT is invalid, It should begin with the country code'), ()

    _constraints = [(check_vat, _construct_constraint_msg, ["vat"])]

    __check_vat_mx_re = re.compile(r"(?P<primeras>[A-Za-z\xd1\xf1&]{3,4})" \
                                    r"[ \-_]?" \
                                    r"(?P<ano>[0-9]{2})(?P<mes>[01][0-9])(?P<dia>[0-3][0-9])" \
                                    r"[ \-_]?" \
                                    r"(?P<code>[A-Za-z0-9&\xd1\xf1]{3})$")

    # Mexican VAT verification is not define in vatnumber library, so we need to define it here
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

    # Sweden VAT number check fails is some cases from vatnumber library..so override this check method here
    def check_vat_se(self, vat):
        '''
        Check Sweden VAT number.
        '''
        if len(vat) != 12:
            return False
        try:
            int(vat)
        except:
            return False
        #if int(vat[9:11]) <= 0: Fixed in OpenERP
        if int(vat[9:11]) < 0:
            return False

        sum = vatnumber.mult_add(2, int(vat[0])) + int(vat[1]) + \
              vatnumber.mult_add(2, int(vat[2])) + int(vat[3]) + \
              vatnumber.mult_add(2, int(vat[4])) + int(vat[5]) + \
              vatnumber.mult_add(2, int(vat[6])) + int(vat[7]) + \
              vatnumber.mult_add(2, int(vat[8]))
        check = 10 - (sum % 10)
        if check == 10:
            check = 0
        if check != int(vat[9]):
            return False
        return True

    # Italy VAT number check fails is some cases from vatnumber library..so override this check method here
    def check_vat_it(self, vat):
        '''
        Check Italy VAT number.
        '''
        if len(vat) != 11:
            return False
        try:
            int(vat)
        except:
            return False
        if int(vat[0:7]) <= 0:
            return False
        if int(vat[7:10]) <= 0:
            return False
        if int(vat[7:10]) > 100 and int(vat[7:10]) < 120:
            return False
#        Fixed in OpenERP
#        if int(vat[7:10]) > 121:
#            return False

        sum = int(vat[0]) + vatnumber.mult_add(2, int(vat[1])) + int(vat[2]) + \
                vatnumber.mult_add(2, int(vat[3])) + int(vat[4]) + \
                vatnumber.mult_add(2, int(vat[5])) + int(vat[6]) + \
                vatnumber.mult_add(2, int(vat[7])) + int(vat[8]) + \
                vatnumber.mult_add(2, int(vat[9]))
        check = 10 - (sum % 10)
        if check == 10:
            check = 0
        if check != int(vat[10]):
            return False
        return True

res_partner()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: