# -*- encoding: utf-8 -*-
#
#  Created by Nicolas Bessi and Vincent Renaville 
#
#  Copyright (c) 2010 CamptoCamp. All rights reserved.
##############################################################################
#
#
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

import wizard
import pooler
import time
from tools.misc import UpdateableStr

FORM = UpdateableStr()
#
class ScanBvr(wizard.interface):
    """Wizzard that will scanan ESR/BVR code line and imprt it to the ERP"""
    supported_type = ['01', '03', '04', '21', '31']
    type_dict = {
        '01' : 'BVR en CHF', 
        '03' : 'BVR-Rbt en CHF                ',
        '04' : 'BVR+ en CHF                                   ',
        '11' : 'BVR en CHF pour propre compte (chiffre 3.3.4) ',
        '14' : 'BVR+ en CHF pour propre compte (chiffre 3.3.4)', 
        '21' : 'BVR en EUR                                    ',
        '23' : 'BVR en EUR pour propre compte (chiffre 3.3.4) ',
        '31' : 'BVR+ en EUR                                   ',
        '33' : 'BVR+ en EUR pour propre compte (chiffre 3.3.4)',
    }
    def _check_number(self, part_validation):
        """Validate modulo 10 of inputed part_validation"""
        n_tab = [0, 9, 4, 6, 8, 2, 7, 1, 3, 5]
        resultnumber = 0
        for number in part_validation:
            resultnumber = n_tab[(resultnumber + int(number) - 0) % 10]
        return (10 - resultnumber) % 10

    def _get_invoice_address(self, cursor, uid, partner_address):
        "Retriev the correct adresses for a partner addresses list"
        valid_address_id = ''
        for partner_address_object in partner_address:
            if partner_address_object.type == "invoice":
                valid_address_id = partner_address_object.id
        if not valid_address_id:
            if len(partner_address) > 0:
                valid_address_id = partner_address[0].id
            else:
                raise wizard.except_wizard(
                                            'AddressError', 
                                            'No Address Assign to this partner'
                                        )
        return valid_address_id
                
    def _construct_bvr(self, bvr_string, intype='standard'):
        """Function that will parde BVR/ESR line and extract the nedded datas
        ref,account, amount and number"""
        amount = 0.0
        if intype == '+' :
            if len(bvr_string)  >43 or len(bvr_string) < 32:
                raise wizard.except_wizard(
                                            'AccountError', 
                                            'code lenght is wrong'
                                            )
        if intype == 'standard':
            if len(bvr_string)  >53 or len(bvr_string) < 42:
                raise wizard.except_wizard(
                                            'AccountError', 
                                            'code lenght is wrong'
                                           )
             
        bvr_type_code_and_valid = bvr_string.split('>')[0]
        bvr_ref = bvr_string.split('+ ')[0].split('>')[1]
        bvr_account = bvr_string.split('+ ')[1].replace('>','')
        if intype == 'standard':
            amount = float(bvr_type_code_and_valid[2:-1])/100.00
        if self._check_number(bvr_type_code_and_valid[:-1]) != \
            int(bvr_type_code_and_valid[-1:]):
            raise wizard.except_wizard(
                                        'AccountError', 
                                        'BVR Mod 10 of type invalid'
                                        )
        elif self._check_number(bvr_ref[:-1]) != int(bvr_ref[-1:]):
            raise wizard.except_wizard(
                                        'AccountError', 
                                        'BVR mod 10 of ref invalid'
                                        )
        elif self._check_number(bvr_account[:-1]) != int(bvr_account[-1:]):
            raise wizard.except_wizard(
                                        'AccountError', 
                                        'BVR Mod 10 of account invalid'
                                       )
        else:
            if (bvr_ref.startswith('000000') and len(bvr_ref)>16) \
                or len(bvr_ref) == 16:
                #it is a post finance customer
                bvrnumber = False
            else :
                bvrnumber = bvr_ref[0:6]
            currency = 'CHF'
            if bvr_ref[-1:] in ('21', '23', '31', '33') :
                currency = 'EUR'
            
                 
            bvr_struct = {
              'type' : bvr_type_code_and_valid[0:-1],
              'amount' : amount,
              'reference' : bvr_ref,
              'bvrnumber' : bvrnumber,
              'beneficiary' : self._create_bvr_account(bvr_account[0:-1]),
              'domain' : '',
              'currency' : currency,
              }
            print bvr_struct
            return bvr_struct
    
    def _create_direct_invoice(self, cursor, uid, data, context):
        """Function that will create a direct invoice"""
        pool = pooler.get_pool(cursor.dbname)
        if data['form']['Account_list']:
            account_info = pool.get('res.partner.bank').browse(
                                                cursor,
                                                uid,
                                                data['form']['Account_list']
                                            )
        ## We will now search the currency_id
        #
        
        #
        currency_search = pool.get('res.currency').search(
                            cursor,
                            uid,
                            [('code', '=', data['bvr_struct']['currency'])]
                        )
        currency_id = pool.get('res.currency').browse(cursor, uid, currency_search[0])
        ## Account Modification
        if data['bvr_struct']['domain'] == 'name':
            pool.get('res.partner.bank').write(
                            cursor,
                            uid,
                            data['form']['Account_list'],
                            {'bvr_number': data['bvr_struct']['beneficiary'] }
                        )
        else:
            pool.get('res.partner.bank').write(
                        cursor,
                        uid,
                        data['form']['Account_list'],
                        {
                            'bvr_adherent_num': data['bvr_struct']['bvrnumber'],
                            'bvr_number': data['bvr_struct']['beneficiary']
                        }
                    )
        date_due = time.strftime('%Y-%m-%d')
        # We will now compute the due date and fixe the payment term
        payment_term_id = account_info.partner_id.property_payment_term and \
            account_info.partner_id.property_payment_term.id or False
        if payment_term_id:
            #We Calculate due_date
            res = pool.get('account.invoice').\
                onchange_payment_term_date_invoice(
                                                    cursor,
                                                    uid,
                                                    [],
                                                    payment_term_id,
                                                    time.strftime('%Y-%m-%d')
                                                )
            date_due = res['value']['date_due']
        ##
        #
        curr_invoice = {
            'name': time.strftime('%Y-%m-%d'),
            'partner_id': account_info.partner_id.id,
            'address_invoice_id': self._get_invoice_address(
                                            cursor,
                                            uid,
                                            account_info.partner_id.address
                                            ),
            'account_id': account_info.partner_id.property_account_payable.id,
            'date_due': date_due,
            'date_invoice': time.strftime('%Y-%m-%d'),
            'payment_term': payment_term_id,
            'reference_type': 'bvr',
            'reference' :  data['bvr_struct']['reference'],
            'amount_total' :  data['bvr_struct']['amount'],
            'check_total' :  data['bvr_struct']['amount'],
            'partner_bank' : account_info.id,
            'comment': '',
            'currency_id': currency_id.id,
            'journal_id' : data['form']['invoice_journal'] ,
            'type': 'in_invoice',
    }
        
        last_invoice = pool.get('account.invoice').create(
                                                            cursor, 
                                                            uid, 
                                                            curr_invoice
                                                        )
        invoices = []
        invoices.append(last_invoice)
        return {
        'domain': "[('id','in', ["+','.join(map(str,invoices))+"])]",
        'name': 'Invoices',
        'view_type': 'form',
        'view_mode': 'form',
        'res_model': 'account.invoice',
        'view_id': False,
        'context': "{'type':'in_invoice'}",
        'type': 'ir.actions.act_window',
        'res_id':invoices
        }
 
    def _create_bvr_account(self,account_unformated):
        """Reformat account form reference"""
        
        account_formated = account_unformated[0:2] + '-' + \
        str(int(account_unformated[2:len(account_unformated)-1])) + '-' +\
        account_unformated[len(account_unformated)-1:len(account_unformated)]
        
        return account_formated
    
    def _get_bvr_structurated(self, bvr_string):
        if bvr_string != False:
            ## We will get the 2 frist digit of the BVR
            ## string in order to now the BVR type of this account
            if bvr_string.startswith('<') :
                raise wizard.except_wizard(
                    'BVR Type not supported any mor by Postfinance', 
                    "Postfinance will charge 0.70.- for this kind of BVR"
                )
            bvr_type = bvr_string[0:2]
            #map old unsupported types
            if bvr_type in ('09','10'):
                bvr_type = '01'
            bvr_struct = {}
            if bvr_type not in self.supported_type :
                raise wizard.except_wizard(
                                            'BVR Type not supported', 
                                            "supported type are"+ 
                                            self.type_dict.__repr__()
                                            )
            if bvr_type in ('01', '03', '21'):
                bvr_struct =  self._construct_bvr(bvr_string)
                if (bvr_struct['bvrnumber'] == '000000'):
                    bvr_struct['domain'] = 'name'
                else:
                    bvr_struct['domain'] = 'bvr_adherent_num'
            ##
            elif bvr_type in ('04','31'):
                ## This BVr is the type of BVR in CHF
                # WE will call the function and Call
                bvr_struct =  self._construct_bvr(bvr_string,'+')
                ## We will test if the BVR have an Adherent Number 
                ## if not we will make the search of the account base on
                ##his name non base on the BVR adherent number
                if (bvr_struct['bvrnumber'] == '000000'):
                    bvr_struct['domain'] = 'name'
                else:
                    bvr_struct['domain'] = 'bvr_adherent_num'
            return bvr_struct

        
    def _validate_account(self, cursor, uid, data, context):
        """Function that will find the account linked to the BVR"""
        # BVR Standrard
        #0100003949753>120000000000234478943216899+ 010001628>
        # BVR without BVr Reference
        #0100000229509>000000013052001000111870316+ 010618955>
        # BVR + In CHF
        #042>904370000000000000007078109+ 010037882>
        # BVR In euro
        #2100000440001>961116900000006600000009284+ 030001625>
        #<060001000313795> 110880150449186+ 43435>
        #<010001000165865> 951050156515104+ 43435>
        #<010001000060190> 052550152684006+ 43435>
        #<100001000070670> 500011000042200+ 56448>
        #<090001000161770> 100977906770930+ 35848>
        pool = pooler.get_pool(cursor.dbname)
        ##
        # Explode and check  the BVR Number and structurate it
        ##
        data['bvr_struct'] = self._get_bvr_structurated(data['form']['bvr_string'])
        ## We will now search the account linked with this BVR
        if data['bvr_struct']['domain'] == 'name':
            partner_bank_search = pool.get('res.partner.bank').search(
                        cursor,
                        uid,
                        [('bvr_number', '=',data['bvr_struct']['beneficiary'])]
                    )
        else:
            partner_bank_search = pool.get('res.partner.bank').search(
                    cursor,
                    uid,
                    [('bvr_adherent_num', '=',data['bvr_struct']['bvrnumber'])]
                )
        if partner_bank_search:
                # we have found the account corresponding to the bvr_adhreent_number
                # so we can directly create the account
                # 
            partner_bank_result = pool.get('res.partner.bank').browse(
                                                        cursor,
                                                        uid,
                                                        partner_bank_search[0]
                                                    )
            data['form']['Account_list'] = partner_bank_result.id
            return 'createdirectinvoice'
        else:
            # we haven't found a valid bvr_adherent_number
            # we will need to create or update 
            #
            FORM.string = '''<?xml version="1.0"?>
                            <form string="Need More informations">
                            <separator string="Partner " colspan="4"/>
                            <field name="Partner_list"/>
                            <separator string="Partner Bank Account" colspan="4"/>
                            <field name="Account_list" domain="[('partner_id', '=', Partner_list),('state', 'in', ['bvrbank','bvrpost'])]" />
                            </form>''' 
            return 'createaccount'

 
    
    _transaction_add_fields = {
    'Partner_list': {
                        'string':'Partner', 
                        'type':'many2one', 
                        'relation':'res.partner', 
                        'required':True
                    },
    'Account_list': {
                        'string':'Partner Account', 
                        'type':'many2one', 
                        'relation':'res.partner.bank', 
                        'required':True
                    },
    'import_account_information': {
                                    'string':'Update Bvr Adherent number of \
                                    this account with the one stored in the \
                                    BVR reference?',
                                     'type':'boolean'},
    }

    _create_form = """<?xml version="1.0"?>
                <form title="BVR Scanning">
                        <separator string="Bvr Scanning Result" colspan="4"/>
                        <field name="bvr_string" colspan="4" > </field>
                        <separator string="Invoice Journal" colspan="4"/>
                        <field name="invoice_journal"/>
                </form>"""
    _create_fields = {
                        'bvr_string': {
                                        'string':'BVR String',
                                        'type':'char',
                                        'size':'128' ,
                                        'required':'true'
                                        },
                        'invoice_journal': {
                                            'string':'Journal', 
                                            'type':'many2one', 
                                            'relation':'account.journal', 
                                            'required':True
                                            },
                }
        
    states = {
                'init' : {
                        'actions' : [], 'result' : {'type':'form',
                        'arch':_create_form, 'fields':_create_fields,
                        'state': [
                                    ('end','Cancel'),
                                    ('create','Create invoice')
                                ]
                        },
                 },
                 'create': {
                        'actions': [],
                        'result' : {
                                    'type': 'choice', 
                                    'next_state': _validate_account 
                                    }
                  },
                 'createaccount': {
                         'actions': [],
                         'result': {
                                    'type': 'form', 
                                    'arch':FORM, 
                                    'fields':_transaction_add_fields, 
                                    'state':[
                                    ('end','Cancel'),
                                    ('createdirectinvoice','Create invoice')
                                ]
                            }              
                  },
                 'createdirectinvoice': {
                        'actions': [],
                        'result' : {
                                        'type': 'action', 
                                        'next_state': 'end',
                                        'action':_create_direct_invoice
                                    }
                 },
    }
ScanBvr('scan.bvr')