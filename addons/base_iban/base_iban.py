# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import string

import netsvc
from osv import fields, osv
from tools.translate import _

# Length of IBAN
_iban_len = {'al':28, 'ad':24, 'at':20, 'be': 16, 'ba': 20, 'bg': 22, 'hr': 21, 'cy': 28,
'cz': 24, 'dk': 18, 'ee': 20, 'fo':18, 'fi': 18, 'fr': 27, 'ge': 22, 'de': 22, 'gi': 23,
'gr': 27, 'gl': 18, 'hu': 28, 'is':26, 'ie': 22, 'il': 23, 'it': 27, 'kz': 20, 'lv': 21,
'lb': 28, 'li': 21, 'lt': 20, 'lu':20 ,'mk': 19, 'mt': 31, 'mu': 30, 'mc': 27, 'gb': 22,
'me': 22, 'nl': 18, 'no': 15, 'pl':28, 'pt': 25, 'ro': 24, 'sm': 27, 'sa': 24, 'rs': 22,
'sk': 24, 'si': 19, 'es': 24, 'se':24, 'ch': 21, 'tn': 24, 'tr': 26}

# Reference Examples of IBAN
_ref_iban = { 'al':'ALkk BBBS SSSK CCCC CCCC CCCC CCCC', 'ad':'ADkk BBBB SSSS CCCC CCCC CCCC',
'at':'ATkk BBBB BCCC CCCC CCCC', 'be': 'BEkk BBBC CCCC CCKK', 'ba': 'BAkk BBBS SSCC CCCC CoKK',
'bg': 'BGkk BBBB SSSS DDCC CCCC CC', 'hr': 'HRkk BBBB BBBC CCCC CCCC C',
'cy': 'CYkk BBBS SSSS CCCC CCCC CCCC CCCC',
'cz': 'CZkk BBBB SSSS SSCC CCCC CCCC', 'dk': 'DKkk BBBB CCCC CCCC CC',
 'ee': 'EEkk BBSS CCCC CCCC CCCK', 'fo': 'FOkk CCCC CCCC CCCC CC',
 'fi': 'FIkk BBBB BBCC CCCC CK', 'fr': 'FRkk BBBB BGGG GGCC CCCC CCCC CKK',
 'ge': 'GEkk BBCC CCCC CCCC CCCC CC', 'de': 'DEkk BBBB BBBB CCCC CCCC CC',
 'gi': 'GIkk BBBB CCCC CCCC CCCC CCC', 'gr': 'GRkk BBBS SSSC CCCC CCCC CCCC CCC',
 'gl': 'GLkk BBBB CCCC CCCC CC', 'hu': 'HUkk BBBS SSSC CCCC CCCC CCCC CCCC',
 'is':'ISkk BBBB SSCC CCCC XXXX XXXX XX', 'ie': 'IEkk AAAA BBBB BBCC CCCC CC',
 'il': 'ILkk BBBN NNCC CCCC CCCC CCC', 'it': 'ITkk KAAA AABB BBBC CCCC CCCC CCC',
 'kz': 'KZkk BBBC CCCC CCCC CCCC', 'lv': 'LVkk BBBB CCCC CCCC CCCC C',
'lb': 'LBkk BBBB AAAA AAAA AAAA AAAA AAAA', 'li': 'LIkk BBBB BCCC CCCC CCCC C',
'lt': 'LTkk BBBB BCCC CCCC CCCC', 'lu': 'LUkk BBBC CCCC CCCC CCCC' ,
'mk': 'MKkk BBBC CCCC CCCC CKK', 'mt': 'MTkk BBBB SSSS SCCC CCCC CCCC CCCC CCC',
'mu': 'MUkk BBBB BBSS CCCC CCCC CCCC CCCC CC', 'mc': 'MCkk BBBB BGGG GGCC CCCC CCCC CKK',
'gb': 'GBkk BBBB SSSS SSCC CCCC CC', 'me': 'MEkk BBBC CCCC CCCC CCCC KK',
'nl': 'NLkk BBBB CCCC CCCC CC', 'no': 'NOkk BBBB CCCC CCK', 'pl':'PLkk BBBS SSSK CCCC CCCC CCCC CCCC',
'pt': 'PTkk BBBB SSSS CCCC CCCC CCCK K', 'ro': 'ROkk BBBB CCCC CCCC CCCC CCCC',
'sm': 'SMkk KAAA AABB BBBC CCCC CCCC CCC', 'sa': 'SAkk BBCC CCCC CCCC CCCC CCCC',
'rs': 'RSkk BBBC CCCC CCCC CCCC KK', 'sk': 'SKkk BBBB SSSS SSCC CCCC CCCC',
'si': 'SIkk BBSS SCCC CCCC CKK', 'es': 'ESkk BBBB GGGG KKCC CCCC CCCC',
'se': 'SEkk BBBB CCCC CCCC CCCC CCCC', 'ch': 'CHkk BBBB BCCC CCCC CCCC C',
'tn': 'TNkk BBSS SCCC CCCC CCCC CCCC', 'tr': 'TRkk BBBB BRCC CCCC CCCC CCCC CC'
}

def _format_iban(string):
    '''
    This function removes all characters from given 'string' that isn't a alpha numeric and converts it to upper case.
    '''
    res = ""
    for char in string:
        if char.isalnum():
            res += char.upper()
    return res

def _pretty_iban(string):
    "return string in groups of four characters separated by a single space"
    res = []
    while string:
        res.append(string[:4])
        string = string[4:]
    return ' '.join(res)

class res_partner_bank(osv.osv):
    _inherit = "res.partner.bank"

    def create(self, cr, uid, vals, context=None):
        #overwrite to format the iban number correctly
        if (vals.get('state',False)=='iban') and vals.get('acc_number', False):
            vals['acc_number'] = _format_iban(vals['acc_number'])
        return super(res_partner_bank, self).create(cr, uid, vals, context)

    def write(self, cr, uid, ids, vals, context=None):
        #overwrite to format the iban number correctly
        if (vals.get('state',False)=='iban') and vals.get('acc_number', False):
            vals['acc_number'] = _format_iban(vals['acc_number'])
        return super(res_partner_bank, self).write(cr, uid, ids, vals, context)

    def check_iban(self, cr, uid, ids, context=None):
        '''
        Check the IBAN number
        '''
        for bank_acc in self.browse(cr, uid, ids, context=context):
            if bank_acc.state<>'iban':
                continue
            iban = _format_iban(bank_acc.acc_number).lower()
            if iban[:2] in _iban_len and len(iban) != _iban_len[iban[:2]]:
                return False
            #the four first digits have to be shifted to the end
            iban = iban[4:] + iban[:4]
            #letters have to be transformed into numbers (a = 10, b = 11, ...)
            iban2 = ""
            for char in iban:
                if char.isalpha():
                    iban2 += str(ord(char)-87)
                else:
                    iban2 += char
            #iban is correct if modulo 97 == 1
            if not int(iban2) % 97 == 1:
                return False
        return True

    def _construct_constraint_msg(self, cr, uid, ids, context=None):

        def default_iban_check(iban_cn):
            return iban_cn[0] in string.ascii_lowercase and iban_cn[1] in string.ascii_lowercase

        iban_country = self.browse(cr, uid, ids)[0].acc_number[:2].lower()
        if default_iban_check(iban_country):
            iban_example = iban_country in _ref_iban and _ref_iban[iban_country] + ' \nWhere A = Account number, B = National bank code, S = Branch code, C = account No, N = branch No, K = National check digits....' or ''
            return _('The IBAN does not seem to be correct. You should have entered something like this %s'), (iban_example)
        return _('The IBAN is invalid, it should begin with the country code'), ()

    def get_bban_from_iban(self, cr, uid, ids, context=None):
        '''
        This function returns the bank account number computed from the iban account number, thanks to the mapping_list dictionary that contains the rules associated to its country.
        '''
        res = {}
        mapping_list = {
         #TODO add rules for others countries
            'be': lambda x: x[4:],
            'fr': lambda x: x[14:],
            'ch': lambda x: x[9:],
            'gb': lambda x: x[14:],
        }
        for record in self.browse(cr, uid, ids, context=context):
            if not record.acc_number:
                res[record.id] = False
                continue
            res[record.id] = False
            for code, function in mapping_list.items():
                if record.acc_number.lower().startswith(code):
                    res[record.id] = function(record.acc_number)
                    break
        return res

    _columns = {
        # Deprecated: we keep it for backward compatibility, to be removed in v7
        # We use acc_number instead of IBAN since v6.1, but we keep this field
        # to not break community modules.
        'iban': fields.related('acc_number', string='IBAN', size=34, readonly=True, help="International Bank Account Number", type="char"),
    }
    _constraints = [(check_iban, _construct_constraint_msg, ["acc_number"])]

res_partner_bank()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
