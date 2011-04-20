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

from osv import osv, fields
from tools.translate import _
import re
import datetime

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

def mult_add(i, j):
    """Sum each digits of the multiplication of i and j."""
    return reduce(lambda x, y: x + int(y), str(i*j), 0)

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
        for partner in self.browse(cr, uid, ids, context=context):
            if not partner.vat:
                continue
            vat_country, vat_number = self._split_vat(partner.vat)
            if not hasattr(self, 'check_vat_' + vat_country):
                return False
            check = getattr(self, 'check_vat_' + vat_country)
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

    # code from the following methods come from Tryton (B2CK)
    # http://www.tryton.org/hgwebdir.cgi/modules/relationship/file/544d1de586d9/party.py
    def check_vat_at(self, vat):
        '''
        Check Austria VAT number.
        '''
        if len(vat) != 9:
            return False
        if vat[0] != 'U':
            return False
        num = vat[1:]
        try:
            int(num)
        except:
            return False
        sum = int(num[0]) + mult_add(2, int(num[1])) + \
                int(num[2]) + mult_add(2, int(num[3])) + \
                int(num[4]) + mult_add(2, int(num[5])) + \
                int(num[6])
        check = 10 - ((sum + 4) % 10)
        if check == 10:
            check = 0
        if int(vat[-1:]) != check:
            return False
        return True

    def check_vat_be(self, vat):
        '''
        Check Belgium VAT number.
        '''
        if len(vat) != 10:
            return False
        try:
            int(vat)
        except:
            return False
        if int(vat[-2:]) != \
                97 - (int(vat[:8]) % 97):
            return False
        return True

    def check_vat_bg(self, vat):
        '''
        Check Bulgaria VAT number.
        '''
        if len(vat) not in [9,10]:
            return False
        try:
            int(vat)
        except:
            return False
        if int(vat[0]) in (2, 3) and \
                int(vat[1:2]) != 22:
            return False
        sum = 4 * int(vat[0]) + 3 * int(vat[1]) + 2 * int(vat[2]) + \
                7 * int(vat[3]) + 6 * int(vat[4]) + 5 * int(vat[5]) + \
                4 * int(vat[6]) + 3 * int(vat[7]) + 2 * int(vat[8])
        check = 11 - (sum % 11)
        if check == 11:
            check = 0
        return True

    def check_vat_cy(self, vat):
        '''
        Check Cyprus VAT number.
        '''
        if len(vat) != 9:
            return False
        try:
            int(vat[:8])
        except:
            return False
        n0 = int(vat[0])
        n1 = int(vat[1])
        n2 = int(vat[2])
        n3 = int(vat[3])
        n4 = int(vat[4])
        n5 = int(vat[5])
        n6 = int(vat[6])
        n7 = int(vat[7])

        def conv(x):
            if x == 0:
                return 1
            elif x == 1:
                return 0
            elif x == 2:
                return 5
            elif x == 3:
                return 7
            elif x == 4:
                return 9
            elif x == 5:
                return 13
            elif x == 6:
                return 15
            elif x == 7:
                return 17
            elif x == 8:
                return 19
            elif x == 9:
                return 21
            return x
        n0 = conv(n0)
        n2 = conv(n2)
        n4 = conv(n4)
        n6 = conv(n6)

        sum = n0 + n1 + n2 + n3 + n4 + n5 + n6 + n7
        check = chr(sum % 26 + 65)
        if check != vat[8]:
            return False
        return True

    def check_vat_cz(self, vat):
        '''
        Check Czech Republic VAT number.
        '''
        if len(vat) not in (8, 9, 10):
            return False
        try:
            int(vat)
        except:
            return False

        if len(vat) == 8:
            if int(vat[0]) not in (0, 1, 2, 3, 4, 5, 6, 7, 8):
                return False
            sum = 8 * int(vat[0]) + 7 * int(vat[1]) + 6 * int(vat[2]) + \
                    5 * int(vat[3]) + 4 * int(vat[4]) + 3 * int(vat[5]) + \
                    2 * int(vat[6])
            check = 11 - (sum % 11)
            if check == 10:
                check = 0
            if check == 11:
                check = 1
            if check != int(vat[7]):
                return False
        elif len(vat) == 9 and int(vat[0]) == 6:
            sum = 8 * int(vat[1]) + 7 * int(vat[2]) + 6 * int(vat[3]) + \
                    5 * int(vat[4]) + 4 * int(vat[5]) + 3 * int(vat[6]) + \
                    2 * int(vat[7])
            check = 9 - ((11 - (sum % 11)) % 10)
            if check != int(vat[8]):
                return False
        elif len(vat) == 9:
            if int(vat[0:2]) > 53 and int(vat[0:2]) < 80:
                return False
            if int(vat[2:4]) < 1:
                return False
            if int(vat[2:4]) > 12 and int(vat[2:4]) < 51:
                return False
            if int(vat[2:4]) > 62:
                return False
            if int(vat[2:4]) in (2, 52) and int(vat[0:2]) % 4 > 0:
                if int(vat[4:6]) < 1:
                    return False
                if int(vat[4:6]) > 28:
                    return False
            if int(vat[2:4]) in (2, 52) and int(vat[0:2]) % 4 == 0:
                if int(vat[4:6]) < 1:
                    return False
                if int(vat[4:6]) > 29:
                    return False
            if int(vat[2:4]) in (4, 6, 9, 11, 54, 56, 59, 61):
                if int(vat[4:6]) < 1:
                    return False
                if int(vat[4:6]) > 30:
                    return False
            if int(vat[2:4]) in (1, 3, 5, 7, 8, 10, 12, 51,
                    53, 55, 57, 58, 60, 62):
                if int(vat[4:6]) < 1:
                    return False
                if int(vat[4:6]) > 31:
                    return False
        elif len(vat) == 10:
            if int(vat[0:2]) < 54:
                return False
            if int(vat[2:4]) < 1:
                return False
            if int(vat[2:4]) > 12 and int(vat[2:4]) < 51:
                return False
            if int(vat[2:4]) > 62:
                return False
            if int(vat[2:4]) in (2, 52) and int(vat[0:2]) % 4 > 0:
                if int(vat[4:6]) < 1:
                    return False
                if int(vat[4:6]) > 28:
                    return False
            if int(vat[2:4]) in (2, 52) and int(vat[0:2]) % 4 == 0:
                if int(vat[4:6]) < 1:
                    return False
                if int(vat[4:6]) > 29:
                    return False
            if int(vat[2:4]) in (4, 6, 9, 11, 54, 56, 59, 61):
                if int(vat[4:6]) < 1:
                    return False
                if int(vat[4:6]) > 30:
                    return False
            if int(vat[2:4]) in (1, 3, 5, 7, 8, 10, 12, 51,
                    53, 55, 57, 58, 60, 62):
                if int(vat[4:6]) < 1:
                    return False
                if int(vat[4:6]) > 31:
                    return False
            if (int(vat[0:2]) + int(vat[2:4]) + int(vat[4:6]) + int(vat[6:8]) +
                    int(vat[8:10])) % 11 != 0:
                return False
            if int(vat[0:10]) % 11 != 0:
                return False
        return True

    def check_vat_de(self, vat):
        '''
        Check Germany VAT number.
        '''
        if len(vat) != 9:
            return False
        try:
            int(vat)
        except:
            return False
        if int(vat[0:7]) <= 0:
            return False
        sum = 0
        for i in range(8):
            sum = (2 * ((int(vat[i]) + sum + 9) % 10 + 1)) % 11
        check = 11 - sum
        if check == 10:
            check = 0
        if int(vat[8]) != check:
            return False
        return True

    def check_vat_dk(self, vat):
        '''
        Check Denmark VAT number.
        '''
        if len(vat) != 8:
            return False
        try:
            int(vat)
        except:
            return False
        if int(vat[0]) <= 0:
            return False
        sum = 2 * int(vat[0]) + 7 * int(vat[1]) + 6 * int(vat[2]) + \
                5 * int(vat[3]) + 4 * int(vat[4]) + 3 * int(vat[5]) + \
                2 * int(vat[6]) + int(vat[7])
        if sum % 11 != 0:
            return False
        return True

    def check_vat_ee(self, vat):
        '''
        Check Estonia VAT number.
        '''
        if len(vat) != 9:
            return False
        try:
            int(vat)
        except:
            return False
        sum = 3 * int(vat[0]) + 7 * int(vat[1]) + 1 * int(vat[2]) + \
                3 * int(vat[3]) + 7 * int(vat[4]) + 1 * int(vat[5]) + \
                3 * int(vat[6]) + 7 * int(vat[7])
        check = 10 - (sum % 10)
        if check == 10:
            check = 0
        if check != int(vat[8]):
            return False
        return True

    def check_vat_es(self, vat):
        '''
        Check Spain VAT number.
        '''
        if len(vat) != 9:
            return False

        conv = {
            1: 'T',
            2: 'R',
            3: 'W',
            4: 'A',
            5: 'G',
            6: 'M',
            7: 'Y',
            8: 'F',
            9: 'P',
            10: 'D',
            11: 'X',
            12: 'B',
            13: 'N',
            14: 'J',
            15: 'Z',
            16: 'S',
            17: 'Q',
            18: 'V',
            19: 'H',
            20: 'L',
            21: 'C',
            22: 'K',
            23: 'E',
        }
        #Legal persons with profit aim
        if vat[0] in ('A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'U', 'V'):
            try:
                int(vat[1:8])
            except:
                return False
            sum = mult_add(2, int(vat[1])) + int(vat[2]) + \
                    mult_add(2, int(vat[3])) + int(vat[4]) + \
                    mult_add(2, int(vat[5])) + int(vat[6]) + \
                    mult_add(2, int(vat[7]))
            check = 10 - (sum % 10)
            if check == 10:
                check = 0
            return True
        #Legal persons with non-profit aim
        elif vat[0] in ('N', 'P', 'Q', 'R', 'S', 'W'):
            try:
                int(vat[1:8])
            except:
                return False
            sum = mult_add(2, int(vat[1])) + int(vat[2]) + \
                    mult_add(2, int(vat[3])) + int(vat[4]) + \
                    mult_add(2, int(vat[5])) + int(vat[6]) + \
                    mult_add(2, int(vat[7]))
            check = 10 - (sum % 10)
            check = chr(check + 64)
            if check != vat[8]:
                return False
            return True
        #Foreign natural persons, under age 14 or non-residents
        elif vat[0] in ('K', 'L', 'M', 'X', 'Y', 'Z'):
            if vat[0] == 'Y':
                check_value = '1' + vat[1:8]
            elif vat[0] == 'Z':
                check_value = '2' + vat[1:8]
            else:
                check_value = vat[1:8]

            try:
                int(check_value)
            except:
                return False
            check = 1 + (int(check_value) % 23)

            check = conv[check]
            if check != vat[8]:
                return False
            return True
        #Spanish natural persons
        else:
            try:
                int(vat[:8])
            except:
                return False
            check = 1 + (int(vat[:8]) % 23)

            check = conv[check]
            if check != vat[8]:
                return False
            return True

    def check_vat_fi(self, vat):
        '''
        Check Finland VAT number.
        '''
        if len(vat) != 8:
            return False
        try:
            int(vat)
        except:
            return False
        sum = 7 * int(vat[0]) + 9 * int(vat[1]) + 10 * int(vat[2]) + \
                5 * int(vat[3]) + 8 * int(vat[4]) + 4 * int(vat[5]) + \
                2 * int(vat[6])
        check = 11 - (sum % 11)
        if check == 11:
            check = 0
        if check == 10:
            return False
        if check != int(vat[7]):
            return False
        return True

    def check_vat_fr(self, vat):
        '''
        Check France VAT number.
        '''
        if len(vat) != 11:
            return False

        try:
            int(vat[2:11])
        except:
            return False

        system = None
        try:
            int(vat[0:2])
            system = 'old'
        except:
            system = 'new'

        if system == 'old':
            check = ((int(vat[2:11]) * 100) + 12) % 97
            if check != int(vat[0:2]):
                return False
            return True
        else:
            conv = ['0', '1', '2', '3', '4', '5', '6', '7',
                '8', '9', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H',
                'J', 'K', 'L', 'M', 'N', 'P', 'Q', 'R', 'S', 'T',
                'U', 'V', 'W', 'X', 'Y', 'Z']
            if vat[0] not in conv \
                    or vat[1] not in conv:
                return False
            c1 = conv.index(vat[0])
            c2 = conv.index(vat[1])

            if c1 < 10:
                sum = c1 * 24 + c2 - 10
            else:
                sum = c1 * 34 + c2 - 100

            x = sum % 11
            sum = (int(sum) / 11) + 1
            y = (int(vat[2:11]) + sum) % 11
            if x != y:
                return False
            return True

    def check_vat_gb(self, vat):
        '''
        Check United Kingdom VAT number.
        '''

        if len(vat) == 5:
            try:
                int(vat[2:5])
            except:
                return False

            if vat[0:2] == 'GD':
                if int(vat[2:5]) >= 500:
                    return False
                return True
            if vat[0:2] == 'HA':
                if int(vat[2:5]) < 500:
                    return False
                return True
            return False
        elif len(vat) in (9, 10):
            try:
                int(vat)
            except:
                return False

            if int(vat[0:7]) < 1:
                return False
            if int(vat[0:7]) > 19999 and int(vat[0:7]) < 1000000:
                return False
            if int(vat[7:9]) > 97:
                return False
            if len(vat) == 10 and int(vat[9]) != 3:
                return False

            sum = 8 * int(vat[0]) + 7 * int(vat[1]) + 6 * int(vat[2]) + \
                    5 * int(vat[3]) + 4 * int(vat[4]) + 3 * int(vat[5]) + \
                    2 * int(vat[6]) + 10 * int(vat[7]) + int(vat[8])
            if int(vat[0:3]) > 100:
                if sum % 97 not in (0, 55, 42):
                    return False
            else:
                if sum % 97 != 0:
                    return False
            return True
        elif len(vat) in (12, 13):
            try:
                int(vat)
            except:
                return False

            if int(vat[0:3]) not in (0, 1):
                return False

            if int(vat[3:10]) < 1:
                return False
            if int(vat[3:10]) > 19999 and int(vat[3:10]) < 1000000:
                return False
            if int(vat[10:12]) > 97:
                return False
            if len(vat) == 13 and int(vat[12]) != 3:
                return False

            sum = 8 * int(vat[3]) + 7 * int(vat[4]) + 6 * int(vat[5]) + \
                    5 * int(vat[6]) + 4 * int(vat[7]) + 3 * int(vat[8]) + \
                    2 * int(vat[9]) + 10 * int(vat[10]) + int(vat[11])
            if sum % 97 != 0:
                return False
            return True
        return False

    def check_vat_gr(self, vat):
        '''
        Check Greece VAT number.
        '''
        try:
            int(vat)
        except:
            return False
        if len(vat) == 8:
            sum = 128 * int(vat[0]) + 64 * int(vat[1]) + 32 * int(vat[2]) + \
                    16 * int(vat[3]) + 8 * int(vat[4]) + 4 * int(vat[5]) + \
                    2 * int(vat[6])
            check = sum % 11
            if check == 10:
                check = 0
            if check != int(vat[7]):
                return False
            return True
        elif len(vat) == 9:
            sum = 256 * int(vat[0]) + 128 * int(vat[1]) + 64 * int(vat[2]) + \
                    32 * int(vat[3]) + 16 * int(vat[4]) + 8 * int(vat[5]) + \
                    4 * int(vat[6]) + 2 * int(vat[7])
            check = sum % 11
            if check == 10:
                check = 0
            if check != int(vat[8]):
                return False
            return True
        return False

    def check_vat_el(self, vat):
        return self.check_vat_gr(vat)

    def check_vat_hu(self, vat):
        '''
        Check Hungary VAT number.
        '''
        if len(vat) != 8:
            return False
        try:
            int(vat)
        except:
            return False
        if int(vat[0]) <= 0:
            return False
        sum = 9 * int(vat[0]) + 7 * int(vat[1]) + 3 * int(vat[2]) + \
                1 * int(vat[3]) + 9 * int(vat[4]) + 7 * int(vat[5]) + \
                3 * int(vat[6])
        check = 10 - (sum % 10)
        if check == 10:
            check = 0
        if check != int(vat[7]):
            return False
        return True

    def check_vat_ie(self, vat):
        '''
        Check Ireland VAT number.
        '''
        if len(vat) != 8:
            return False
        if (ord(vat[1]) >= 65 and ord(vat[1]) <= 90) \
                or vat[1] in ('+', '*'):
            try:
                int(vat[0])
                int(vat[2:7])
            except:
                return False

            if int(vat[0]) <= 6:
                return False

            sum = 7 * int(vat[2]) + 6 * int(vat[3]) + 5 * int(vat[4]) + \
                    4 * int(vat[5]) + 3 * int(vat[6]) + 2 * int(vat[0])
            check = sum % 23
            if check == 0:
                check = 'W'
            else:
                check = chr(check + 64)
            if check != vat[7]:
                return False
            return True
        else:
            try:
                int(vat[0:7])
            except:
                return False

            sum = 8 * int(vat[0]) + 7 * int(vat[1]) + 6 * int(vat[2]) + \
                    5 * int(vat[3]) + 4 * int(vat[4]) + 3 * int(vat[5]) + \
                    2 * int(vat[6])
            check = sum % 23
            if check == 0:
                check = 'W'
            else:
                check = chr(check + 64)
            if check != vat[7]:
                return False
            return True

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

        sum = int(vat[0]) + mult_add(2, int(vat[1])) + int(vat[2]) + \
                mult_add(2, int(vat[3])) + int(vat[4]) + \
                mult_add(2, int(vat[5])) + int(vat[6]) + \
                mult_add(2, int(vat[7])) + int(vat[8]) + \
                mult_add(2, int(vat[9]))
        check = 10 - (sum % 10)
        if check == 10:
            check = 0
        if check != int(vat[10]):
            return False
        return True

    def check_vat_lt(self, vat):
        '''
        Check Lithuania VAT number.
        '''
        try:
            int(vat)
        except:
            return False

        if len(vat) == 9:
            if int(vat[7]) != 1:
                return False
            sum = 1 * int(vat[0]) + 2 * int(vat[1]) + 3 * int(vat[2]) + \
                    4 * int(vat[3]) + 5 * int(vat[4]) + 6 * int(vat[5]) + \
                    7 * int(vat[6]) + 8 * int(vat[7])
            if sum % 11 == 10:
                sum = 3 * int(vat[0]) + 4 * int(vat[1]) + 5 * int(vat[2]) + \
                        6 * int(vat[3]) + 7 * int(vat[4]) + 8 * int(vat[5]) + \
                        9 * int(vat[6]) + 1 * int(vat[7])
            check = sum % 11
            if check == 10:
                check = 0
            if check != int(vat[8]):
                return False
            return True
        elif len(vat) == 12:
            if int(vat[10]) != 1:
                return False
            sum = 1 * int(vat[0]) + 2 * int(vat[1]) + 3 * int(vat[2]) + \
                    4 * int(vat[3]) + 5 * int(vat[4]) + 6 * int(vat[5]) + \
                    7 * int(vat[6]) + 8 * int(vat[7]) + 9 * int(vat[8]) + \
                    1 * int(vat[9]) + 2 * int(vat[10])
            if sum % 11 == 10:
                sum = 3 * int(vat[0]) + 4 * int(vat[1]) + 5 * int(vat[2]) + \
                        6 * int(vat[3]) + 7 * int(vat[4]) + 8 * int(vat[5]) + \
                        9 * int(vat[6]) + 1 * int(vat[7]) + 2 * int(vat[8]) + \
                        3 * int(vat[9]) + 4 * int(vat[10])
            check = sum % 11
            if check == 10:
                check = 0
            if check != int(vat[11]):
                return False
            return True
        return False

    def check_vat_lu(self, vat):
        '''
        Check Luxembourg VAT number.
        '''
        if len(vat) != 8:
            return False
        try:
            int(vat)
        except:
            return False
        if int(vat[0:6]) <= 0:
            return False
        check = int(vat[0:6]) % 89
        if check != int(vat[6:8]):
            return False
        return True

    def check_vat_lv(self, vat):
        '''
        Check Latvia VAT number.
        '''
        if len(vat) != 11:
            return False
        try:
            int(vat)
        except:
            return False
        if int(vat[0]) >= 4:
            sum = 9 * int(vat[0]) + 1 * int(vat[1]) + 4 * int(vat[2]) + \
                    8 * int(vat[3]) + 3 * int(vat[4]) + 10 * int(vat[5]) + \
                    2 * int(vat[6]) + 5 * int(vat[7]) + 7 * int(vat[8]) + \
                    6 * int(vat[9])
            if sum % 11 == 4 and int(vat[0]) == 9:
                sum = sum - 45
            if sum % 11 == 4:
                check = 4 - (sum % 11)
            elif sum % 11 > 4:
                check = 14 - (sum % 11)
            elif sum % 11 < 4:
                check = 3 - (sum % 11)
            if check != int(vat[10]):
                return False
            return True
        else:
            if int(vat[2:4]) == 2 and int(vat[4:6]) % 4 > 0:
                if int(vat[0:2]) < 1 or int(vat[0:2]) > 28:
                    return False
            if int(vat[2:4]) == 2 and int(vat[4:6]) % 4 == 0:
                if int(vat[0:2]) < 1 or int(vat[0:2]) > 29:
                    return False
            if int(vat[2:4]) in (4, 6, 9, 11):
                if int(vat[0:2]) < 1 or int(vat[0:2]) > 30:
                    return False
            if int(vat[2:4]) in (1, 3, 5, 7, 8, 10, 12):
                if int(vat[0:2]) < 1 or int(vat[0:2]) > 31:
                    return False
            if int(vat[2:4]) < 1 or int(vat[2:4]) > 12:
                return False
            return True

    def check_vat_mt(self, vat):
        '''
        Check Malta VAT number.
        '''
        if len(vat) != 8:
            return False
        try:
            int(vat)
        except:
            return False

        if int(vat[0:6]) < 100000:
            return False

        sum = 3 * int(vat[0]) + 4 * int(vat[1]) + 6 * int(vat[2]) + \
                7 * int(vat[3]) + 8 * int(vat[4]) + 9 * int(vat[5])
        check = 37 - (sum % 37)
        if check != int(vat[6:8]):
            return False
        return True

    def check_vat_nl(self, vat):
        '''
        Check Netherlands VAT number.
        '''
        if len(vat) != 12:
            return False
        try:
            int(vat[0:9])
            int(vat[10:12])
        except:
            return False
        if int(vat[0:8]) <= 0:
            return False
        if vat[9] != 'B':
            return False

        sum = 9 * int(vat[0]) + 8 * int(vat[1]) + 7 * int(vat[2]) + \
                6 * int(vat[3]) + 5 * int(vat[4]) + 4 * int(vat[5]) + \
                3 * int(vat[6]) + 2 * int(vat[7])

        check = sum % 11
        if check == 10:
            return False
        if check != int(vat[8]):
            return False
        return True

    def check_vat_pl(self, vat):
        '''
        Check Poland VAT number.
        '''
        if len(vat) != 10:
            return False
        try:
            int(vat)
        except:
            return False

        sum = 6 * int(vat[0]) + 5 * int(vat[1]) + 7 * int(vat[2]) + \
                2 * int(vat[3]) + 3 * int(vat[4]) + 4 * int(vat[5]) + \
                5 * int(vat[6]) + 6 * int(vat[7]) + 7 * int(vat[8])
        check = sum % 11
        if check == 10:
            return False
        if check != int(vat[9]):
            return False
        return True

    def check_vat_pt(self, vat):
        '''
        Check Portugal VAT number.
        '''
        if len(vat) != 9:
            return False
        try:
            int(vat)
        except:
            return False

        if int(vat[0]) <= 0:
            return False

        sum = 9 * int(vat[0]) + 8 * int(vat[1]) + 7 * int(vat[2]) + \
                6 * int(vat[3]) + 5 * int(vat[4]) + 4 * int(vat[5]) + \
                3 * int(vat[6]) + 2 * int(vat[7])
        check = 11 - (sum % 11)
        if check == 10 or check == 11:
            check = 0
        return True

    def check_vat_ro(self, vat):
        '''
        Check Romania VAT number.
        '''
        try:
            int(vat)
        except:
            return False

        if len(vat) >= 2 and len(vat) <= 10:
            vat = (10 - len(vat)) * '0' + vat
            sum = 7 * int(vat[0]) + 5 * int(vat[1]) + 3 * int(vat[2]) + \
                    2 * int(vat[3]) + 1 * int(vat[4]) + 7 * int(vat[5]) + \
                    5 * int(vat[6]) + 3 * int(vat[7]) + 2 * int(vat[8])
            check = (sum * 10) % 11
            if check == 10:
                check = 0
            if check != int(vat[9]):
                return False
            return True
        elif len(vat) == 13:
            if int(vat[0]) not in (1, 2, 3, 4, 6):
                return False
            if int(vat[3:5]) < 1 or int(vat[3:5]) > 12:
                return False
            if int(vat[3:5]) == 2 and int(vat[1:3]) % 4 > 0:
                if int(vat[5:7]) < 1 or int(vat[5:7]) > 28:
                    return False
            if int(vat[3:5]) == 2 and int(vat[1:3]) % 4 == 0:
                if int(vat[5:7]) < 1 or int(vat[5:7]) > 29:
                    return False
            if int(vat[3:5]) in (4, 6, 9, 11):
                if int(vat[5:7]) < 1 or int(vat[5:7]) > 30:
                    return False
            if int(vat[3:5]) in (1, 3, 5, 7, 8, 10, 12):
                if int(vat[5:7]) < 1 or int(vat[5:7]) > 31:
                    return False

            sum = 2 * int(vat[0]) + 7 * int(vat[1]) + 9 * int(vat[2]) + \
                    1 * int(vat[3]) + 4 * int(vat[4]) + 6 * int(vat[5]) + \
                    3 * int(vat[6]) + 5 * int(vat[7]) + 8 * int(vat[8]) + \
                    2 * int(vat[9]) + 7 * int(vat[10]) + 9 * int(vat[11])
            check = sum % 11
            if check == 10:
                check = 1
            if check != int(vat[12]):
                return False
            return True
        return False

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

        if int(vat[9:11]) < 0:
            return False

        sum = mult_add(2, int(vat[0])) + int(vat[1]) + \
                mult_add(2, int(vat[2])) + int(vat[3]) + \
                mult_add(2, int(vat[4])) + int(vat[5]) + \
                mult_add(2, int(vat[6])) + int(vat[7]) + \
                mult_add(2, int(vat[8]))
        check = 10 - (sum % 10)
        if check == 10:
            check = 0
        if check != int(vat[9]):
            return False
        return True

    def check_vat_si(self, vat):
        '''
        Check Slovenia VAT number.
        '''
        if len(vat) != 8:
            return False
        try:
            int(vat)
        except:
            return False
        if int(vat[0:7]) <= 999999:
            return False

        sum = 8 * int(vat[0]) + 7 * int(vat[1]) + 6 * int(vat[2]) + \
                5 * int(vat[3]) + 4 * int(vat[4]) + 3 * int(vat[5]) + \
                2 * int(vat[6])
        check = 11 - (sum % 11)
        if check == 10:
            check = 0
        if check == 11:
            check = 1
        if check != int(vat[7]):
            return False
        return True

    def check_vat_sk(self, vat):
        '''
        Check Slovakia VAT number.
        '''
        try:
            int(vat)
        except:
            return False
        if len(vat) not in(9, 10):
            return False

        if int(vat[0:2]) in (0, 10, 20) and len(vat) == 10:
            return True

        if len(vat) == 10:
            if int(vat[0:2]) < 54 or int(vat[0:2]) > 99:
                return False

        if len(vat) == 9:
            if int(vat[0:2]) > 53 :
                return False

        if int(vat[2:4]) < 1:
            return False
        if int(vat[2:4]) > 12 and int(vat[2:4]) < 51:
            return False
        if int(vat[2:4]) > 62:
            return False
        if int(vat[2:4]) in (2, 52) and int(vat[0:2]) % 4 > 0:
            if int(vat[4:6]) < 1 or int(vat[4:6]) > 28:
                return False
        if int(vat[2:4]) in (2, 52) and int(vat[0:2]) % 4 == 0:
            if int(vat[4:6]) < 1 or int(vat[4:6]) > 29:
                return False
        if int(vat[2:4]) in (4, 6, 9, 11, 54, 56, 59, 61):
            if int(vat[4:6]) < 1 or int(vat[4:6]) > 30:
                return False
        if int(vat[2:4]) in (1, 3, 5, 7, 8, 10, 12,
                51, 53, 55, 57, 58, 60, 62):
            if int(vat[4:6]) < 1 or int(vat[4:6]) > 31:
                return False
        return True

    __check_vat_mx_re = re.compile(r"(?P<primeras>[A-Z&ñÑ]{3,4})" \
                                    r"[ \-_]?" \
                                    r"(?P<ano>[0-9]{2})(?P<mes>[01][1-9])(?P<dia>[0-3][0-9])" \
                                    r"[ \-_]?" \
                                    r"(?P<code>[A-Z0-9&ñÑ\xd1\xf1]{3})$")
    
    def check_vat_mx(vat):
        ''' Mexican VAT verification
        
        Verificar RFC México
        '''
        m = self.__check_vat_mx_re.match(vat)
        if not m:
            #No valid format
            return False
        try:
            datetime.date(int(m.group('ano')), int(m.group('mes')), int(m.group('dia')))
        except ValueError:
            return False
        
        #Valid format and valid date
        return True
        
res_partner()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
