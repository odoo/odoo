# -*- encoding: utf-8 -*-
#
#  dta_wizard.py
#  l10n_ch
#
#  Created by Nicolas Bessi based on Credric Krier contribution
#
#  Copyright (c) 2010 CamptoCamp. All rights reserved.
##############################################################################
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################
"""Wizard that will generate a DTA payment order file. 
See dta.ch for getting specification"""
import pooler
import wizard
import base64
import time
import pooler
import codecs
import unicodedata
import mx.DateTime
from tools.translate import _


FORM = """<?xml version="1.0"?>
<form string="DTA file creation - Results">
<separator colspan="4" string="Clic on 'Save as' to save the DTA file :" />
    <field name="dta"/>
</form>"""

FIELDS = {
    'dta': {
        'string': 'DTA File',
        'type': 'binary',
        'readonly': True,
    },
}

def trim_string(string_in, key=None):
    "Manage line encoding"
    try:
        string_in = u''.join((c for c in unicodedata.normalize('NFD', string_in) \
            if unicodedata.category(c) != 'Mn'))
        string_in.encode('ascii','ignore')
        return string_in
    except Exception, encode_err:
        print  key, encode_err
        return string_in

##See Tech spec www.dta.ch chapter 3.4
class Record:
    """Record class that represents a DTA recore (a line in the file)"""

    def __init__(self, global_context_dict):
        for i in global_context_dict:
            global_context_dict[i] = global_context_dict[i] \
                    and trim_string(global_context_dict[i],i)
        #print global_context_dict
        self.fields = []
        self.global_values = global_context_dict
        self.pre = {
            'padding': u'',
            'seg_num1': u'01',
            'seg_num2': u'02',
            'seg_num3': u'03',
            'seg_num4': u'04',
            'seg_num5': u'05',
            'flag': u'0',
            'zero5': u'00000'
        }
        self.post={'date_value_hdr': u'000000', 'type_paiement': u'0'}
        self.init_local_context()

    def init_local_context(self):
        """Abstract function that is used to instanciate a record segemnt"""
        """
        Must instanciate a fields list, field = (name,size)
        and update a local_values dict.
        """
        raise _('not implemented')

    def generate(self):
        """Generate a DTA line"""
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
                #raise Exception(field[0]+' not found !')
            try:
                res = res + c_ljust(value, field[1])
            except :
                pass
        return res


class RecordGt826(Record):
    """
    bvr type record see chapter 4.2 for more details
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
            'date_value': u'',
            'partner_bank_clearing': u'',
            'partner_cpt_benef': u'',
            'genre_trans': '826',
            'conv_cours': u'',
            'option_id_bank': 'D',
            'partner_bvr': u'/C/'+ self.global_values['partner_bvr'],
            'ref2': u'',
            'ref3': u'',
            'format': u'0',
        })

class RecordGt827(Record):
    """
    interne suisse (bvpost et bvbank) see chapter 4.3
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
            'date_value_hdr':self.global_values['date_value'],
            'date_value': u'',
            'partner_cpt_benef': u'',
            'type_paiement': u'0',
            'genre_trans': u'827',
            'conv_cours': u'',
            'option_id_bank': u'D',
            'ref2': u'',
            'ref3': u'',
            'format': u'0'
        })


class RecordGt836(Record):
    """
    iban see chapter 4.6
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


class RecordGt890(Record):
    """
    Total see chapter 4.8
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
        self.pre.update({'partner_bank_clearing': u'', 'partner_cpt_benef': u'',
            'company_bank_clearing': u'', 'genre_trans': u'890'})

def c_ljust(input_string, size):
    """
    check before calling ljust
    """
    try:
        input_string= input_string or ''
        if len(input_string) > size:
            input_string= input_string[:size]
        input_string = input_string.decode('utf-8').\
            encode('latin1','replace').ljust(size)
    except Exception, e:
        return input_string.ljust(size) 

    return input_string

def _create_dta(obj, cr, uid, data, context):
    """Generate DTA file"""
    v={}
    v['uid'] = unicode(uid)
    v['creation_date']= unicode(time.strftime('%y%m%d'))
    dta=''
    pool = pooler.get_pool(cr.dbname)
    payment_obj = pool.get('payment.order')
    attachment_obj = pool.get('ir.attachment')

    payment = payment_obj.browse(cr, uid, data['id'], context=context)

    if not payment.mode or payment.mode.type.code != 'dta':
        raise wizard.except_wizard(_('Error'),
                _('No payment mode or payment type code invalid.'))
    bank = payment.mode.bank_id
    if not bank:
        raise wizard.except_wizard(
                                    _('Error'), 
                                    _('No bank account for the company.')
                                )

    v['comp_bank_name']= bank.bank and bank.bank.name or False
    v['comp_bank_clearing'] = bank.bank.clearing

    if not v['comp_bank_clearing']:
        raise wizard.except_wizard(_('Error'),
                _('You must provide a Clearing Number for your bank account.'))

    user = pool.get('res.users').browse(cr,uid,[uid])[0]
    company= user.company_id
    co_addr= company.partner_id.address[0]
    v['comp_country'] = co_addr.country_id and co_addr.country_id.name or u''
    v['comp_street'] = co_addr.street or u''
    v['comp_zip'] = co_addr.zip
    v['comp_city'] = co_addr.city
    v['comp_name'] = co_addr.name
    v['comp_dta'] = bank.dta_code or u''


    v['comp_bank_number'] = bank.acc_number or u''
    if bank.iban:
        v['comp_bank_iban'] = bank.iban.replace(u' ',u'') or u''
    else:
        v['comp_bank_iban'] = ''
    if not v['comp_bank_iban']:
        raise wizard.except_wizard(_('Error'),
                _('No IBAN for the company bank account.'))

    dta_line_obj = pool.get('account.dta.line')
    res_partner_bank_obj = pool.get('res.partner.bank')

    seq= 1
    amount_tot = 0
    amount_currency_tot = 0

    for pline in payment.line_ids:
        if not pline.bank_id:
            raise wizard.except_wizard(
                                        _('Error'), 
                                        _('No bank account defined\n'+
                                        'on line: %s') % pline.name)
        if not pline.bank_id.bank:
            raise wizard.except_wizard(
                                        _('Error'),
                                        _('No bank defined\n'+
                                        'for the bank account: %s\n'+
                                        'on the partner: %s\n'+
                                        'on line: %s') + (
                                            pline.bank_id.state, 
                                            pline.partner_id.name, 
                                            pline.name
                                            )
                                    )
        acc_name = res_partner_bank_obj.name_get(
                                                cr, 
                                                uid, 
                                                [pline.bank_id.id], 
                                                context
                                            )[0][1]

        v['sequence'] = unicode(seq).rjust(5).replace(u' ', u'0')
        v['amount_to_pay']= unicode(pline.amount_currency).replace(u'.', u',')
        v['number'] = pline.name
        v['currency'] = pline.currency.code

        v['partner_bank_name'] =  pline.bank_id.bank.name or False
        v['partner_bank_clearing'] =  pline.bank_id.bank.clearing or False
        if not v['partner_bank_name'] :
            raise wizard.except_wizard(
                                        _('Error'), 
                                        _('No bank name defined\n' +
                                        'for the bank account: %s\n' +
                                        'on the partner: %s\n' +
                                        'on line: %s') % (
                                                        pline.bank_id.state, 
                                                        pline.partner_id.name, 
                                                        pline.name
                                                        )
                                        )

        v['partner_bank_iban']=  pline.bank_id.iban or False
        v['partner_bank_number']=  pline.bank_id.acc_number  \
            and pline.bank_id.acc_number.replace(u'.',u'').replace(u'-',u'') \
            or  False
        v['partner_post_number']=  pline.bank_id.post_number \
        and pline.bank_id.post_number.replace(u'.', u'').replace(u'-', u'') \
        or  False
        v['partner_bvr'] = pline.bank_id.bvr_number or u''
        if v['partner_bvr']:
            v['partner_bvr'] = v['partner_bvr'].replace(u'-',u'')
            if len(v['partner_bvr']) < 9:
                v['partner_bvr'] = v['partner_bvr'][:2] + '0' * \
                        (9 - len(v['partner_bvr'])) + v['partner_bvr'][2:]

        if pline.bank_id.bank:
            v['partner_bank_city'] = pline.bank_id.bank.city or False
            v['partner_bank_street'] = pline.bank_id.bank.street or u''
            v['partner_bank_zip'] = pline.bank_id.bank.zip or u''
            v['partner_bank_country'] = pline.bank_id.bank.country and \
                    pline.bank_id.bank.country.name or u''

        v['partner_bank_code'] = pline.bank_id.bank.bic
        v['reference'] = pline.move_line_id.ref
        # Add support for owner of the account if exists..
        if pline.bank_id.owner_name:
            v['partner_name'] = pline.bank_id.owner_name
        else:
            v['partner_name'] = pline.partner_id and \
                pline.partner_id.name or u''
        
        if pline.partner_id and pline.partner_id.address \
                and pline.partner_id.address[0]:
            v['partner_street'] = pline.partner_id.address[0].street
            v['partner_city']= pline.partner_id.address[0].city
            v['partner_zip']= pline.partner_id.address[0].zip
            # If iban => country=country code for space reason
            elec_pay = pline.bank_id.state #Bank type
            if elec_pay == 'iban':
                v['partner_country']= pline.partner_id.address[0].country_id \
                        and pline.partner_id.address[0].country_id.code+u'-' \
                        or u''
            else:
                v['partner_country']= pline.partner_id.address[0].country_id \
                        and pline.partner_id.address[0].country_id.name \
                        or ''
        else:
            v['partner_street'] =u''
            v['partner_city']= u''
            v['partner_zip']= u''
            v['partner_country']= u''
            raise wizard.except_wizard('Error', 'No address defined \n'+
                    'for the partner: ' + pline.partner_id.name + '\n'+
                    'on line: ' + pline.name)

        if pline.order_id.date_planned :
            date_value = mx.DateTime.strptime(
                                                pline.order_id.date_planned, 
                                                '%Y-%m-%d'
                                            )
        elif pline.date :
            date_value = mx.DateTime.strptime(pline.date, '%Y-%m-%d')
        else :
            date_value = mx.DateTime.now()
        v['date_value'] = unicode(date_value.strftime("%y%m%d"))

        # si compte iban -> iban (836)
        # si payment structure  -> bvr (826)
        # si non -> (827) 

        if elec_pay == 'dta_iban':
            # If iban => country=country code for space reason
            v['comp_country'] = co_addr.country_id and \
                co_addr.country_id.code+'-' or ''
            record_type = RecordGt836
            if not v['partner_bank_iban']:
                raise wizard.except_wizard(
                                            _('Error'), 
                                            _('No IBAN defined \n'+
                                            'for the bank account: %s\n'+
                                            'on line: %s') % (
                                                                acc_name , 
                                                                pline.name
                                                            )
                                            )

            if v['partner_bank_code'] : # bank code is swift (BIC address)
                v['option_id_bank']= u'A'
                v['partner_bank_ident']= v['partner_bank_code']
            elif v['partner_bank_city']:

                v['option_id_bank']= u'D'
                v['partner_bank_ident']= v['partner_bank_name'] \
                        + ' ' + v['partner_bank_street'] \
                        + ' ' + v['partner_bank_zip'] \
                        + ' ' + v['partner_bank_city'] \
                        + ' ' + v['partner_bank_country']
            else:
                raise wizard.except_wizard(
                            _('Error'), 
                            _('You must provide the bank city ' +
                            'and the bic code for the partner bank: \n %s\n' +
                            'on line: %s') %(acc_name, pline.name)
                        )

        elif elec_pay == 'bvrbank' or elec_pay == 'bvrpost':
            from tools import mod10r
            if v['reference']:
                v['reference'] = v['reference'].replace(' ',
                        '').rjust(27).replace(u' ', u'0')
                if not v['reference'] \
                    or (mod10r(v['reference'][:-1]) != v['reference'] and \
                    not len(v['reference']) == 15):
                    raise wizard.except_wizard(
                                            _('Error'), 
                                            _('You must provide '+
                                            'a valid BVR reference number \n'+
                                            'for the line: %s') % pline.name)
            if not v['partner_bvr']:
                raise wizard.except_wizard(
                    _('Error'), 
                    _('You must provide a BVR number\n'+
                    'for the bank account: %s'+
                    'on line: %s') % (acc_name ,pline.name))
            record_type = RecordGt826

        elif elec_pay == 'bvbank':
            if not v['partner_bank_number'] :
                if v['partner_bank_iban'] :
                    v['partner_bank_number']= v['partner_bank_iban'] 
                else:
                    raise wizard.except_wizard(
                                    _('Error'), 
                                    _('You must provide '+
                                    'a bank number \n'+
                                    'for the partner bank: %s\n'+
                                    'on line: %s') % ( acc_name, pline.name)
                                )
            if not  v['partner_bank_clearing']:
                raise wizard.except_wizard(
                                        _('Error'), 
                                        _('You must provide '+
                                        'a Clearing Number\n'+
                                        'for the partner bank: %s\n'+
                                        'on line %s') % (
                                                            acc_name , 
                                                            pline.name
                                                            )
                                                        )
            v['partner_bank_number'] = '/C/'+v['partner_bank_number']
            record_type = RecordGt827
        elif elec_pay == 'bvpost':
            if not v['partner_post_number']:
                raise wizard.except_wizard(
                                            _('Error'), 
                                            _('You must provide '+
                                            'a post number \n'+
                                            'for the partner bank: %s\n'+
                                            'on line: %s') % (
                                                                acc_name,
                                                                pline.name
                                                            )
                                        )
            v['partner_bank_clearing']= ''
            v['partner_bank_number'] = '/C/'+v['partner_post_number']
            record_type = RecordGt827
        else:
            raise wizard.except_wizard(
                                        _('Error'),
                                        _('The Bank type %s of the bank'+
                                        'account: %s is not supported') \
                                        %(elec_pay, acc_name)
                                    )

        dta_line = record_type(v).generate()

        dta = dta + dta_line
        amount_tot += pline.amount
        amount_currency_tot += pline.amount_currency
        seq += 1

    # segment total
    v['amount_total'] = unicode(amount_currency_tot).replace(u'.',u',')
    v['sequence'] = unicode(seq).rjust(5).replace(u' ',u'0')  
    if dta :
        dta = dta + RecordGt890(v).generate()

    dta_data= base64.encodestring(dta.encode('utf8'))
    payment_obj.set_done(cr, uid, data['id'], context)
    attachment_obj.create(cr, uid, {
        'name': 'DTA',
        'datas': dta_data,
        'datas_fname': 'DTA.txt',
        'res_model': 'payment.order',
        'res_id': data['id'],
        }, context=context)
    return {'dta': dta_data}


class WizardDtaCreate(wizard.interface):
    """Wizard that will generate a DTA payment order file.
     See www.dta.ch for getting specification"""
    states = {
        'init' : {
            'actions' : [_create_dta],
            'result' : {'type' : 'form',
                'arch' : FORM,
                'fields' : FIELDS,
                'state' : [('end', 'OK', 'gtk-ok', True)]
            }
        },
    }

WizardDtaCreate('account.dta_create')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
