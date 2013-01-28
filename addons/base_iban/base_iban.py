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

from openerp.osv import fields, osv
from openerp.tools.translate import _

# Reference Examples of IBAN
_ref_iban = { 'al':'ALkk BBBS SSSK CCCC CCCC CCCC CCCC', 'ad':'ADkk BBBB SSSS CCCC CCCC CCCC',
'at':'ATkk BBBB BCCC CCCC CCCC', 'be': 'BEkk BBBC CCCC CCKK', 'ba': 'BAkk BBBS SSCC CCCC CCKK',
'bg': 'BGkk BBBB SSSS DDCC CCCC CC', 'bh': 'BHkk BBBB SSSS SSSS SSSS SS',
'cr': 'CRkk BBBC CCCC CCCC CCCC C',
'hr': 'HRkk BBBB BBBC CCCC CCCC C', 'cy': 'CYkk BBBS SSSS CCCC CCCC CCCC CCCC',
'cz': 'CZkk BBBB SSSS SSCC CCCC CCCC', 'dk': 'DKkk BBBB CCCC CCCC CC',
'do': 'DOkk BBBB CCCC CCCC CCCC CCCC CCCC',
 'ee': 'EEkk BBSS CCCC CCCC CCCK', 'fo': 'FOkk CCCC CCCC CCCC CC',
 'fi': 'FIkk BBBB BBCC CCCC CK', 'fr': 'FRkk BBBB BGGG GGCC CCCC CCCC CKK',
 'ge': 'GEkk BBCC CCCC CCCC CCCC CC', 'de': 'DEkk BBBB BBBB CCCC CCCC CC',
 'gi': 'GIkk BBBB CCCC CCCC CCCC CCC', 'gr': 'GRkk BBBS SSSC CCCC CCCC CCCC CCC',
 'gl': 'GLkk BBBB CCCC CCCC CC', 'hu': 'HUkk BBBS SSSC CCCC CCCC CCCC CCCC',
 'is':'ISkk BBBB SSCC CCCC XXXX XXXX XX', 'ie': 'IEkk BBBB SSSS SSCC CCCC CC',
 'il': 'ILkk BBBS SSCC CCCC CCCC CCC', 'it': 'ITkk KBBB BBSS SSSC CCCC CCCC CCC',
 'kz': 'KZkk BBBC CCCC CCCC CCCC', 'kw': 'KWkk BBBB CCCC CCCC CCCC CCCC CCCC CC',
 'lv': 'LVkk BBBB CCCC CCCC CCCC C',
'lb': 'LBkk BBBB CCCC CCCC CCCC CCCC CCCC', 'li': 'LIkk BBBB BCCC CCCC CCCC C',
'lt': 'LTkk BBBB BCCC CCCC CCCC', 'lu': 'LUkk BBBC CCCC CCCC CCCC' ,
'mk': 'MKkk BBBC CCCC CCCC CKK', 'mt': 'MTkk BBBB SSSS SCCC CCCC CCCC CCCC CCC',
'mr': 'MRkk BBBB BSSS SSCC CCCC CCCC CKK',
'mu': 'MUkk BBBB BBSS CCCC CCCC CCCC CCCC CC', 'mc': 'MCkk BBBB BGGG GGCC CCCC CCCC CKK',
'me': 'MEkk BBBC CCCC CCCC CCCC KK',
'nl': 'NLkk BBBB CCCC CCCC CC', 'no': 'NOkk BBBB CCCC CCK',
'pl':'PLkk BBBS SSSK CCCC CCCC CCCC CCCC',
'pt': 'PTkk BBBB SSSS CCCC CCCC CCCK K', 'ro': 'ROkk BBBB CCCC CCCC CCCC CCCC',
'sm': 'SMkk KBBB BBSS SSSC CCCC CCCC CCC', 'sa': 'SAkk BBCC CCCC CCCC CCCC CCCC',
'rs': 'RSkk BBBC CCCC CCCC CCCC KK', 'sk': 'SKkk BBBB SSSS SSCC CCCC CCCC',
'si': 'SIkk BBSS SCCC CCCC CKK', 'es': 'ESkk BBBB SSSS KKCC CCCC CCCC',
'se': 'SEkk BBBB CCCC CCCC CCCC CCCC', 'ch': 'CHkk BBBB BCCC CCCC CCCC C',
'tn': 'TNkk BBSS SCCC CCCC CCCC CCCC', 'tr': 'TRkk BBBB BRCC CCCC CCCC CCCC CC',
'ae': 'AEkk BBBC CCCC CCCC CCCC CCC',
'gb': 'GBkk BBBB SSSS SSCC CCCC CC',
}

def _format_iban(iban_str):
    '''
    This function removes all characters from given 'iban_str' that isn't a alpha numeric and converts it to upper case.
    '''
    res = ""
    if iban_str:
        for char in iban_str:
            if char.isalnum():
                res += char.upper()
    return res

def _pretty_iban(iban_str):
    "return iban_str in groups of four characters separated by a single space"
    res = []
    while iban_str:
        res.append(iban_str[:4])
        iban_str = iban_str[4:]
    return ' '.join(res)

class res_partner_bank(osv.osv):
    _inherit = "res.partner.bank"

    def create(self, cr, uid, vals, context=None):
        #overwrite to format the iban number correctly
        if (vals.get('state',False)=='iban') and vals.get('acc_number', False):
            vals['acc_number'] = _format_iban(vals['acc_number'])
            vals['acc_number'] = _pretty_iban(vals['acc_number'])
        return super(res_partner_bank, self).create(cr, uid, vals, context)

    def write(self, cr, uid, ids, vals, context=None):
        #overwrite to format the iban number correctly
        if (vals.get('state',False)=='iban') and vals.get('acc_number', False):
            vals['acc_number'] = _format_iban(vals['acc_number'])
            vals['acc_number'] = _pretty_iban(vals['acc_number'])
        return super(res_partner_bank, self).write(cr, uid, ids, vals, context)

    def is_iban_valid(self, cr, uid, iban, context=None):
        """ Check if IBAN is valid or not
            @param iban: IBAN as string
            @return: True if IBAN is valid, False otherwise
        """
        if not iban:
            return False
        iban = _format_iban(iban).lower()
        if iban[:2] in _ref_iban and len(iban) != len(_format_iban(_ref_iban[iban[:2]])):
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
        return int(iban2) % 97 == 1

    def check_iban(self, cr, uid, ids, context=None):
        '''
        Check the IBAN number
        '''
        for bank_acc in self.browse(cr, uid, ids, context=context):
            if bank_acc.state != 'iban':
                continue
            if not self.is_iban_valid(cr, uid, bank_acc.acc_number, context=context):
                return False
        return True

    def _construct_constraint_msg(self, cr, uid, ids, context=None):

        def default_iban_check(iban_cn):
             return iban_cn and iban_cn[0] in string.ascii_lowercase and iban_cn[1] in string.ascii_lowercase

        iban_country = self.browse(cr, uid, ids)[0].acc_number and self.browse(cr, uid, ids)[0].acc_number[:2].lower()
        if default_iban_check(iban_country):
            if iban_country in _ref_iban:
                return _('The IBAN does not seem to be correct. You should have entered something like this %s'), \
                        ('%s \nWhere B = National bank code, S = Branch code,'\
                         ' C = Account No, K = Check digit' % _ref_iban[iban_country])
            return _('This IBAN does not pass the validation check, please verify it'), ()
        return _('The IBAN is invalid, it should begin with the country code'), ()

    def _check_bank(self, cr, uid, ids, context=None):
        for partner_bank in self.browse(cr, uid, ids, context=context):
            if partner_bank.state == 'iban' and not partner_bank.bank.bic:
                return False
        return True

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
    _constraints = [
        (check_iban, _construct_constraint_msg, ["iban"]),
        (_check_bank, '\nPlease define BIC/Swift code on bank for bank type IBAN Account to make valid payments', ['bic'])
    ]

res_partner_bank()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
