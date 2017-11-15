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
import re
import string

from openerp.osv import fields, osv
from openerp.tools.translate import _

# Reference Examples of IBAN
_ref_iban = { 
    'ad': 'ADkk BBBB SSSS CCCC CCCC CCCC',  # Andorra
    'ae': 'AEkk BBBC CCCC CCCC CCCC CCC',  # United Arab Emirates
    'al': 'ALkk BBBS SSSK CCCC CCCC CCCC CCCC',  # Albania
    'at': 'ATkk BBBB BCCC CCCC CCCC',  # Austria
    'az': 'AZkk BBBB CCCC CCCC CCCC CCCC CCCC',  # Azerbaijan
    'ba': 'BAkk BBBS SSCC CCCC CCKK',  # Bosnia and Herzegovina
    'be': 'BEkk BBBC CCCC CCXX',  # Belgium
    'bg': 'BGkk BBBB SSSS DDCC CCCC CC',  # Bulgaria
    'bh': 'BHkk BBBB CCCC CCCC CCCC CC',  # Bahrain
    'br': 'BRkk BBBB BBBB SSSS SCCC CCCC CCCT N',  # Brazil
    'ch': 'CHkk BBBB BCCC CCCC CCCC C',  # Switzerland
    'cr': 'CRkk BBBC CCCC CCCC CCCC C',  # Costa Rica
    'cy': 'CYkk BBBS SSSS CCCC CCCC CCCC CCCC',  # Cyprus
    'cz': 'CZkk BBBB SSSS SSCC CCCC CCCC',  # Czech Republic
    'de': 'DEkk BBBB BBBB CCCC CCCC CC',  # Germany
    'dk': 'DKkk BBBB CCCC CCCC CC',  # Denmark
    'do': 'DOkk BBBB CCCC CCCC CCCC CCCC CCCC',  # Dominican Republic
    'ee': 'EEkk BBSS CCCC CCCC CCCK',  # Estonia
    'es': 'ESkk BBBB SSSS KKCC CCCC CCCC',  # Spain
    'fi': 'FIkk BBBB BBCC CCCC CK',  # Finland
    'fo': 'FOkk CCCC CCCC CCCC CC',  # Faroe Islands
    'fr': 'FRkk BBBB BGGG GGCC CCCC CCCC CKK',  # France
    'gb': 'GBkk BBBB SSSS SSCC CCCC CC',  # United Kingdom
    'ge': 'GEkk BBCC CCCC CCCC CCCC CC',  # Georgia
    'gi': 'GIkk BBBB CCCC CCCC CCCC CCC',  # Gibraltar
    'gl': 'GLkk BBBB CCCC CCCC CC',  # Greenland
    'gr': 'GRkk BBBS SSSC CCCC CCCC CCCC CCC',  # Greece
    'gt': 'GTkk BBBB MMTT CCCC CCCC CCCC CCCC',  # Guatemala
    'hr': 'HRkk BBBB BBBC CCCC CCCC C',  # Croatia
    'hu': 'HUkk BBBS SSSC CCCC CCCC CCCC CCCC',  # Hungary
    'ie': 'IEkk BBBB SSSS SSCC CCCC CC',  # Ireland
    'il': 'ILkk BBBS SSCC CCCC CCCC CCC',  # Israel
    'is': 'ISkk BBBB SSCC CCCC XXXX XXXX XX',  # Iceland
    'it': 'ITkk KBBB BBSS SSSC CCCC CCCC CCC',  # Italy
    'jo': 'JOkk BBBB NNNN CCCC CCCC CCCC CCCC CC',  # Jordan
    'kw': 'KWkk BBBB CCCC CCCC CCCC CCCC CCCC CC',  # Kuwait
    'kz': 'KZkk BBBC CCCC CCCC CCCC',  # Kazakhstan
    'lb': 'LBkk BBBB CCCC CCCC CCCC CCCC CCCC',  # Lebanon
    'li': 'LIkk BBBB BCCC CCCC CCCC C',  # Liechtenstein
    'lt': 'LTkk BBBB BCCC CCCC CCCC',  # Lithuania
    'lu': 'LUkk BBBC CCCC CCCC CCCC',  # Luxembourg
    'lv': 'LVkk BBBB CCCC CCCC CCCC C',  # Latvia
    'mc': 'MCkk BBBB BGGG GGCC CCCC CCCC CKK',  # Monaco
    'md': 'MDkk BBCC CCCC CCCC CCCC CCCC',  # Moldova
    'me': 'MEkk BBBC CCCC CCCC CCCC KK',  # Montenegro
    'mk': 'MKkk BBBC CCCC CCCC CKK',  # Macedonia
    'mr': 'MRkk BBBB BSSS SSCC CCCC CCCC CKK',  # Mauritania
    'mt': 'MTkk BBBB SSSS SCCC CCCC CCCC CCCC CCC',  # Malta
    'mu': 'MUkk BBBB BBSS CCCC CCCC CCCC CCCC CC',  # Mauritius
    'nl': 'NLkk BBBB CCCC CCCC CC',  # Netherlands
    'no': 'NOkk BBBB CCCC CCK',  # Norway
    'pk': 'PKkk BBBB CCCC CCCC CCCC CCCC',  # Pakistan
    'pl': 'PLkk BBBS SSSK CCCC CCCC CCCC CCCC',  # Poland
    'ps': 'PSkk BBBB XXXX XXXX XCCC CCCC CCCC C',  # Palestinian
    'pt': 'PTkk BBBB SSSS CCCC CCCC CCCK K',  # Portugal
    'qa': 'QAkk BBBB CCCC CCCC CCCC CCCC CCCC C',  # Qatar
    'ro': 'ROkk BBBB CCCC CCCC CCCC CCCC',  # Romania
    'rs': 'RSkk BBBC CCCC CCCC CCCC KK',  # Serbia
    'sa': 'SAkk BBCC CCCC CCCC CCCC CCCC',  # Saudi Arabia
    'se': 'SEkk BBBB CCCC CCCC CCCC CCCC',  # Sweden
    'si': 'SIkk BBSS SCCC CCCC CKK',  # Slovenia
    'sk': 'SKkk BBBB SSSS SSCC CCCC CCCC',  # Slovakia
    'sm': 'SMkk KBBB BBSS SSSC CCCC CCCC CCC',  # San Marino
    'tn': 'TNkk BBSS SCCC CCCC CCCC CCCC',  # Tunisia
    'tr': 'TRkk BBBB BRCC CCCC CCCC CCCC CC',  # Turkey
    'vg': 'VGkk BBBB CCCC CCCC CCCC CCCC',  # Virgin Islands
    'xk': 'XKkk BBBB CCCC CCCC CCCC',  # Kosovo
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

def normalize_iban(iban):
    return re.sub('[\W_]', '', iban or '')

def validate_iban(iban):
    iban = normalize_iban(iban)
    if not iban:
        return False

    country_code = iban[:2].lower()

    if country_code not in _ref_iban:
        return False

    iban_template = _ref_iban[country_code]
    if len(iban) != len(iban_template.replace(' ', '')):
        return False

    check_chars = iban[4:] + iban[:4]
    # BASE 36: 0..9,A..Z -> 0..35
    digits = int(''.join(str(int(char, 36)) for char in check_chars))
    return digits % 97 == 1

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
        return validate_iban(iban)

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
        (check_iban, _construct_constraint_msg, ["iban", "acc_number", "state"]),
        (_check_bank, '\nPlease define BIC/Swift code on bank for bank type IBAN Account to make valid payments', ['bic'])
    ]


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
