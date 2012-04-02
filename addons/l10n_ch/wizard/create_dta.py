# -*- encoding: utf-8 -*-
##############################################################################
#
#    Author: Nicolas Bessi. Copyright Camptocamp SA
#    Donors: Hasa Sàrl, Open Net Sàrl and Prisme Solutions Informatique SA
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

import time
from datetime import datetime
import base64

from osv import osv, fields
import pooler
from tools.translate import _
import unicode2ascii

import re

TRANS=[
    (u'é','e'),
    (u'è','e'),
    (u'à','a'),
    (u'ê','e'),
    (u'î','i'),
    (u'ï','i'),
    (u'â','a'),
    (u'ä','a'),
]

def _u2a(text) :
    """Tries to convert unicode charactere to asci equivalence"""
    if not text : return ""
    txt = ""
    for c in text:
        if ord(c) < 128 :
            txt += c
        elif c in unicode2ascii.EXTRA_LATIN_NAMES :
            txt += unicode2ascii.EXTRA_LATIN_NAMES[c]
        elif c in unicode2ascii.UNI2ASCII_CONVERSIONS :
            txt += unicode2ascii.UNI2ASCII_CONVERSIONS[c]
        elif c in unicode2ascii.EXTRA_CHARACTERS :
            txt += unicode2ascii.EXTRA_CHARACTERS[c]
        elif c in unicode2ascii.FG_HACKS :
            txt += unicode2ascii.FG_HACKS[c]
        else : txt+= "_"
    return txt

def tr(string_in):
    try:
        string_in= string_in.decode('utf-8')
    except:
        # If exception => then just take the string as is
        pass
    for k in TRANS:
        string_in = string_in.replace(k[0],k[1])
    try:
        res= string_in.encode('ascii','replace')
    except:
        res = string_in
    return res


class record:
    def __init__(self, global_context_dict):
        for i in global_context_dict:
            global_context_dict[i] = global_context_dict[i] \
                    and tr(global_context_dict[i])
        self.fields = []
        self.global_values = global_context_dict
        self.pre = {
            'padding': '',
            'seg_num1': '01',
            'seg_num2': '02',
            'seg_num3': '03',
            'seg_num4': '04',
            'seg_num5': '05',
            'flag': '0',
            'zero5': '00000'
        }
        self.post={'date_value_hdr': '000000', 'type_paiement': '0'}
        self.init_local_context()

    def init_local_context(self):
        """
        Must instanciate a fields list, field = (name,size)
        and update a local_values dict.
        """
        raise _('not implemented')

    def generate(self):
        res=''
        for field in self.fields :
            if self.pre.has_key(field[0]):
                value = self.pre[field[0]]
            elif self.global_values.has_key(field[0]):
                value = self.global_values[field[0]]
            elif self.post.has_key(field[0]):
                value = self.post[field[0]]
            else :
                pass
            try:
                res = res + c_ljust(value, field[1])
            except :
                pass
        return res


class record_gt826(record):
    """
    bvr
    """
    def init_local_context(self):
        self.fields=[
            ('seg_num1', 2),
            #header
            ('date_value_hdr', 6),
            ('partner_bank_clearing', 12),
            ('zero5', 5),
            ('creation_date', 6),
            ('comp_bank_clearing', 7),
            ('uid', 5),
            ('sequence', 5),
            ('genre_trans', 3),
            ('type_paiement', 1),
            ('flag', 1),
            #seg1
            ('comp_dta', 5),
            ('number', 11),
            ('comp_bank_iban', 24),
            ('date_value', 6),
            ('currency', 3),
            ('amount_to_pay', 12),
            ('padding', 14),
            #seg2
            ('seg_num2', 2),
            ('comp_name', 20),
            ('comp_street', 20),
            ('comp_zip', 10),
            ('comp_city', 10),
            ('comp_country', 20),
            ('padding', 46),
            #seg3
            ('seg_num3', 2),
            ('partner_bvr', 12),#numero d'adherent bvr
            ('partner_name', 20),
            ('partner_street', 20),
            ('partner_zip', 10),
            ('partner_city', 10),
            ('partner_country', 20),
            ('reference', 27),#communication structuree
            ('padding', 2),#cle de controle
            ('padding', 5)
        ]
        self.pre.update({
            'date_value_hdr': self.global_values['date_value'],
            'date_value': '',
            'partner_bank_clearing': '',
            'partner_cpt_benef': '',
            'genre_trans': '826',
            'conv_cours': '',
            'option_id_bank': 'D',
            'partner_bvr': '/C/'+ self.global_values['partner_bvr'],
            'ref2': '',
            'ref3': '',
            'format': '0',
        })

class record_gt827(record):
    """
    interne suisse (bvpost et bvbank)
    """
    def init_local_context(self):
        self.fields = [
            ('seg_num1', 2),
            #header
            ('date_value_hdr', 6),
            ('partner_bank_clearing', 12),
            ('zero5', 5),
            ('creation_date', 6),
            ('comp_bank_clearing', 7),
            ('uid', 5),
            ('sequence', 5),
            ('genre_trans', 3),
            ('type_paiement', 1),
            ('flag', 1),
            #seg1
            ('comp_dta', 5),
            ('number', 11),
            ('comp_bank_iban', 24),
            ('date_value', 6),
            ('currency', 3),
            ('amount_to_pay', 12),
            ('padding', 14),
            #seg2
            ('seg_num2', 2),
            ('comp_name', 20),
            ('comp_street', 20),
            ('comp_zip', 10),
            ('comp_city', 10),
            ('comp_country', 20),
            ('padding', 46),
            #seg3
            ('seg_num3', 2),
            ('partner_bank_number', 30),
            ('partner_name', 24),
            ('partner_street', 24),
            ('partner_zip', 12),
            ('partner_city', 12),
            ('partner_country', 24),
            #seg4
            ('seg_num4', 2),
            ('reference', 112),
            ('padding', 14),
            #seg5
            #('padding',128)
            ]

        self.pre.update({
            'date_value_hdr': self.global_values['date_value'],
            'date_value': '',
            'partner_cpt_benef': '',
            'type_paiement': '0',
            'genre_trans': '827',
            'conv_cours': '',
            'option_id_bank': 'D',
            'ref2': '',
            'ref3': '',
            'format': '0'
        })


class record_gt836(record):
    """
    iban
    """
    def init_local_context(self):
        self.fields = [
            ('seg_num1', 2),
            #header
            ('date_value_hdr', 6),
            ('partner_bank_clearing', 12),
            ('zero5', 5),
            ('creation_date', 6),
            ('comp_bank_clearing', 7),
            ('uid', 5),
            ('sequence', 5),
            ('genre_trans', 3),
            ('type_paiement', 1),
            ('flag', 1),
            #seg1
            ('comp_dta', 5),
            ('number', 11),
            ('comp_bank_iban', 24),
            ('date_value', 6),
            ('currency', 3),
            ('amount_to_pay', 15),
            ('padding', 11),
            #seg2
            ('seg_num2', 2),
            ('conv_cours', 12),
            ('comp_name', 35),
            ('comp_street', 35),
            ('comp_country', 3),
            ('comp_zip', 10),
            ('comp_city', 22),
            ('padding', 9),
            #seg3
            ('seg_num3', 2),
            ('option_id_bank', 1),
            ('partner_bank_ident', 70),
            ('partner_bank_iban', 34),
            ('padding', 21),
            #seg4
            ('seg_num4', 2),
            ('partner_name', 35),
            ('partner_street', 35),
            ('partner_country', 3),
            ('partner_zip', 10),
            ('partner_city', 22),
            ('padding', 21),
            #seg5
            ('seg_num5', 2),
            ('option_motif', 1),
            ('reference', 105),
            ('format', 1),
            ('padding', 19)
        ]
        self.pre.update( {
            'partner_bank_clearing': '',
            'partner_cpt_benef': '',
            'type_paiement': '0',
            'genre_trans': '836',
            'conv_cours': '',
            'reference': self.global_values['reference'],
            'ref2': '',
            'ref3': '',
            'format': '2'
        })
        self.post.update({'option_motif': 'U'})


class record_gt890(record):
    """
    Total
    """
    def init_local_context(self):
        self.fields = [
            ('seg_num1', 2),
            #header
            ('date_value_hdr', 6),
            ('partner_bank_clearing', 12),
            ('zero5', 5),
            ('creation_date', 6),
            ('comp_bank_clearing', 7),
            ('uid', 5),
            ('sequence', 5),
            ('genre_trans', 3),
            ('type_paiement', 1),
            ('flag', 1),
            #total
            ('amount_total', 16),
            ('padding', 59)
        ]
        self.pre.update({'partner_bank_clearing': '', 'partner_cpt_benef': '',
            'company_bank_clearing': '', 'genre_trans': '890'})

def c_ljust(s, size):
    """
    check before calling ljust
    """
    s= s or ''
    if len(s) > size:
        s= s[:size]
    s = s.decode('utf-8').encode('latin1','replace').ljust(size)
    return s

def _is_9_pos_bvr_adherent(adherent_num):
    """
    from a bvr adherent number,
    return true if 
    """
    pattern = r'[0-9]{2}-[0-9]{1,6}-[0-9]'
    return re.search(pattern, adherent_num)

def _create_dta(obj, cr, uid, data, context=None):
    v = {}
    v['uid'] = str(uid)
    v['creation_date'] = time.strftime('%y%m%d')
    dta = ''

    pool = pooler.get_pool(cr.dbname)
    payment_obj = pool.get('payment.order')
    attachment_obj = pool.get('ir.attachment')
    if context is None:
        context = {}
    payment = payment_obj.browse(cr, uid, data['id'], context=context)
    # if payment.state != 'done':
        # raise osv.except_osv(_('Order not confirmed'),
        #         _('Please confirm it'))
    if not payment.mode:
        raise osv.except_osv(_('Error'),
                _('No payment mode'))
    bank = payment.mode.bank_id
    if not bank:
        raise osv.except_osv(_('Error'), _('No bank account for the company.'))

    v['comp_bank_name']= bank.bank and bank.bank.name or False
    v['comp_bank_clearing'] = bank.bank.clearing

    if not v['comp_bank_clearing']:
        raise osv.except_osv(_('Error'),
                _('You must provide a Clearing Number for your bank account.'))

    user = pool.get('res.users').browse(cr,uid,[uid])[0]
    company = user.company_id
    #XXX dirty code use get_addr
    co_addr = company.partner_id
    v['comp_country'] = co_addr.country_id and co_addr.country_id.name or ''
    v['comp_street'] = co_addr.street or ''
    v['comp_zip'] = co_addr.zip
    v['comp_city'] = co_addr.city
    v['comp_name'] = co_addr.name
    v['comp_dta'] = bank.dta_code or '' #XXX not mandatory in pratice

    # iban and account number are the same field and depends only on the type of account
    v['comp_bank_iban'] = v['comp_bank_number'] = bank.acc_number or ''
    
    #if bank.iban:
    #    v['comp_bank_iban'] = bank.iban.replace(' ','') or ''
    #else:
    #    v['comp_bank_iban'] = ''
    if not v['comp_bank_iban']:
        raise osv.except_osv(_('Error'),
                _('No IBAN for the company bank account.'))

    res_partner_bank_obj = pool.get('res.partner.bank')

    seq = 1
    amount_tot = 0
    amount_currency_tot = 0

    for pline in payment.line_ids:
        if not pline.bank_id:
            raise osv.except_osv(_('Error'), _('No bank account defined\n' \
                    'on line: %s') % pline.name)
        if not pline.bank_id.bank:
            raise osv.except_osv(_('Error'), _('No bank defined\n' \
                    'for the bank account: %s\n' \
                    'on the partner: %s\n' \
                    'on line: %s') + (pline.bank_id.state, pline.partner_id.name, pline.name))

        v['sequence'] = str(seq).rjust(5).replace(' ', '0')
        v['amount_to_pay']= str(pline.amount_currency).replace('.', ',')
        v['number'] = pline.name
        v['currency'] = pline.currency.name

        v['partner_bank_name'] =  pline.bank_id.bank.name or False
        v['partner_bank_clearing'] =  pline.bank_id.bank.clearing or False
        if not v['partner_bank_name'] :
            raise osv.except_osv(_('Error'), _('No bank name defined\n' \
                    'for the bank account: %s\n' \
                    'on the partner: %s\n' \
                    'on line: %s') % (pline.bank_id.state, pline.partner_id.name, pline.name))

        v['partner_bank_iban'] =  pline.bank_id.acc_number or False
        v['partner_bank_number'] =  pline.bank_id.acc_number  \
                and pline.bank_id.acc_number.replace('.','').replace('-','') \
                or  False
        v['partner_post_number']=  pline.bank_id.post_number \
                and pline.bank_id.post_number.replace('.', '').replace('-', '') \
                or  False
        v['partner_bvr'] = pline.bank_id.post_number or ''
        if v['partner_bvr']:
            is_9_pos_adherent = None
            # if adherent bvr number is a 9 pos number
            # add 0 to fill 2nd part plus remove '-'
            # exemple: 12-567-C becomes 12000567C
            if _is_9_pos_bvr_adherent(v['partner_bvr']):
                parts = v['partner_bvr'].split('-')
                parts[1] = parts[1].rjust(6, '0')
                v['partner_bvr'] = ''.join(parts)
                is_9_pos_adherent = True
            # add 4*0 to bvr adherent number with 5 pos
            # exemple: 12345 becomes 000012345
            elif len(v['partner_bvr']) == 5:
                v['partner_bvr'] = v['partner_bvr'].rjust(9, '0')
                is_9_pos_adherent = False
            else:
                raise osv.except_osv(_('Error'),
                                     _('Wrong postal number format.\n'
                                       'It must be 12-123456-9 or 12345 format'))

        if pline.bank_id.bank:
            v['partner_bank_city'] = pline.bank_id.bank.city or False
            v['partner_bank_street'] = pline.bank_id.bank.street or ''
            v['partner_bank_zip'] = pline.bank_id.bank.zip or ''
            v['partner_bank_country'] = pline.bank_id.bank.country and \
                    pline.bank_id.bank.country.name or ''

        v['partner_bank_code'] = pline.bank_id.bank.bic
        v['reference'] = pline.move_line_id.ref
        # Add support for owner of the account if exists..
        if pline.bank_id.owner_name:
            v['partner_name'] = pline.bank_id.owner_name
        else:
            v['partner_name'] = pline.partner_id and pline.partner_id.name or ''

        if pline.partner_id and pline.partner_id:
            v['partner_street'] = pline.partner_id.street
            v['partner_city'] = pline.partner_id.city
            v['partner_zip'] = pline.partner_id.zip
            # If iban => country=country code for space reason
            elec_pay = pline.bank_id.state #Bank type
            if elec_pay == 'iban':
                v['partner_country']= pline.partner_id.country_id \
                        and pline.partner_id.country_id.code+'-' \
                        or ''
            else:
                v['partner_country']= pline.partner_id.country_id \
                        and pline.partner_id.country_id.name \
                        or ''
        else:
            v['partner_street'] =''
            v['partner_city']= ''
            v['partner_zip']= ''
            v['partner_country']= ''
            raise osv.except_osv('Error', 'No address defined \n' \
                    'for the partner: ' + pline.partner_id.name + '\n' \
                    'on line: ' + pline.name)

        if pline.order_id.date_scheduled:
            date_value = datetime.strptime(pline.order_id.date_scheduled, '%Y-%m-%d')
        elif pline.date:
            date_value = datetime.strptime(pline.date, '%Y-%m-%d')
        else:
            date_value = datetime.now()
        v['date_value'] = date_value.strftime("%y%m%d")

        # si compte iban -> iban (836)
        # si payment structure  -> bvr (826)
        # si non -> (827)

        if elec_pay == 'iban':
            # If iban => country=country code for space reason
            v['comp_country'] = co_addr.country_id and co_addr.country_id.code+'-' or ''
            record_type = record_gt836
            if not v['partner_bank_iban']:
                raise osv.except_osv(_('Error'), _('No IBAN defined \n' \
                        'for the bank account: %s\n' + \
                        'on line: %s') % (res_partner_bank_obj.name_get(cr, uid, [pline.bank_id.id], context)[0][1] , pline.name))

            if v['partner_bank_code'] : # bank code is swift (BIC address)
                v['option_id_bank']= 'A'
                v['partner_bank_ident']= v['partner_bank_code']
            elif v['partner_bank_city']:

                v['option_id_bank']= 'D'
                v['partner_bank_ident']= v['partner_bank_name'] \
                        + ' ' + v['partner_bank_street'] \
                        + ' ' + v['partner_bank_zip'] \
                        + ' ' + v['partner_bank_city'] \
                        + ' ' + v['partner_bank_country']
            else:
                raise osv.except_osv(_('Error'), _('You must provide the bank city '
                        'or the bic code for the partner bank: \n %d\n' + \
                        'on line: %s') %(res_partner_bank_obj.name_get(cr, uid, [pline.bank_id.id], context)[0][1], pline.name))

        elif elec_pay == 'bvrbank' or elec_pay == 'bvrpost':
            from tools import mod10r
            if not v['reference']:
                raise osv.except_osv(_('Error'), 
                                     _('You must provide ' \
                                       'a BVR reference number \n' \
                                       'for the line: %s') % pline.name)
            v['reference'] = v['reference'].replace(' ', '')
            if is_9_pos_adherent:
                if len(v['reference']) > 27: 
                    raise osv.except_osv(_('Error'),
                                         _('BVR reference number is not valid \n' 
                                           'for the line: %s. \n'
                                           'Reference is too long.') % pline.name)
                # do a mod10 check
                if mod10r(v['reference'][:-1]) != v['reference']:
                    raise osv.except_osv(_('Error'),
                                         _('BVR reference number is not valid \n'
                                           'for the line: %s. \n'
                                           'Mod10 check failed') % pline.name)
                # fill reference with 0
                v['reference'] = v['reference'].rjust(27, '0')
            else:
                # reference of BVR adherent with 5 positions number
                # have 15 positions references
                if len(v['reference']) > 15:
                    raise osv.except_osv(_('Error'),
                                         _('BVR reference number is not valid \n'
                                           'for the line: %s. \n'
                                           'Reference is too long '
                                           'for this type of beneficiary.') % pline.name)
                # complete 15 first digit with 0 on left and complete 27 digits with trailing spaces
                # exemple: 123456 becomes 00000000012345____________
                v['reference'] = v['reference'].rjust(15, '0').ljust(27, ' ')

            if not v['partner_bvr']:
                raise osv.except_osv(_('Error'), _('You must provide a BVR number\n'
                    'for the bank account: %s' \
                    'on line: %s') % (res_partner_bank_obj.name_get(cr, uid, [pline.bank_id.id],context)[0][1] ,pline.name))
            record_type = record_gt826

        elif elec_pay == 'bvbank':
            if not v['partner_bank_number'] :
                raise osv.except_osv(_('Error'), _('You must provide ' \
                        'a bank number \n' \
                        'for the partner bank: %s\n' \
                        'on line: %s') % (res_partner_bank_obj.name_get(cr, uid, [pline.bank_id.id], context)[0][1] , pline.name))
            if not  v['partner_bank_clearing']:
                raise osv.except_osv(_('Error'), _('You must provide ' \
                        'a Clearing Number\n' \
                        'for the partner bank: %s\n' \
                        'on line %s') % (res_partner_bank_obj.name_get(cr, uid, [pline.bank_id.id], context)[0][1] , pline.name))
            v['partner_bank_number'] = '/C/'+v['partner_bank_number']
            record_type = record_gt827
        elif elec_pay == 'bvpost':
            if not v['partner_post_number']:
                raise osv.except_osv(_('Error'), _('You must provide ' \
                        'a post number \n' \
                        'for the partner bank: %s\n' \
                        'on line: %s') % (res_partner_bank_obj.name_get(cr, uid, [pline.bank_id.id], context)[0][1] ,pline.name))
            v['partner_bank_clearing']= ''
            v['partner_bank_number'] = '/C/'+v['partner_post_number']
            record_type = record_gt827
        else:
            raise osv.except_osv(_('Error'), _('The Bank type %s of the bank account: %s is not supported') \
                    % (elec_pay, res_partner_bank_obj.name_get(cr, uid, [pline.bank_id.id], context)[0][1],))

        dta_line = record_type(v).generate()

        dta = dta + dta_line
        amount_tot += pline.amount
        amount_currency_tot += pline.amount_currency
        seq += 1

    # segment total
    v['amount_total'] = str(amount_currency_tot).replace('.',',')
    v['sequence'] = str(seq).rjust(5).replace(' ','0')
    if dta :
        dta = dta + record_gt890(v).generate()
    dta_data = _u2a(dta)
    dta_data = base64.encodestring(dta)
    payment_obj.set_done(cr, uid, [data['id']], context)
    attachment_obj.create(cr, uid, {
        'name': 'DTA%s'%time.strftime("%Y-%m-%d_%H:%M:%S", time.gmtime()),
        'datas': dta_data,
        'datas_fname': 'DTA%s.txt'%time.strftime("%Y-%m-%d_%H:%M:%S", time.gmtime()),
        'res_model': 'payment.order',
        'res_id': data['id'],
        }, context=context)
    return dta_data

class create_dta_wizard(osv.osv_memory):
    _name="create.dta.wizard"

    _columns={
        'dta_file':fields.binary('DTA File', readonly=True)
    }
    def create_dta(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        if isinstance(ids, list):
            req_id = ids[0]
        else:
            req_id = ids
        current = self.browse(cr, uid, req_id, context)
        data = {}
        active_ids = context.get('active_ids', [])
        active_id = context.get('active_id', [])
        data['form'] = {}
        data['ids'] = active_ids
        data['id'] = active_id
        dta_file = _create_dta(self, cr, uid, data, context)
        current.write({'dta_file': dta_file})
        return True

create_dta_wizard()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
