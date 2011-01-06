# -*- encoding: utf-8 -*-
#
#  opae_wizard.py
#  l10n_ch
#
#  Created by J. Bove
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
### Complete rewriting of this code should be done but certification delay are the first may
import wizard
import pooler
from mx import DateTime
import pdb
import base64
import codecs
import unicodedata
from tools.translate import _
####This code is a fisrst prototype that will be rewritten 
### in middle term in order to ensure line validation and functunality extention
"""Code under developpement not functional YET"""

FORM = """<?xml version="1.0"?>
<form string="OPAE file creation - Results">
<separator colspan="4" string="Clic on 'Save as' to save the OPAE file :" />
    <field name="opae"/>
</form>"""

FIELDS = {
        'opae': {
        'string': 'DTA File',
        'type': 'binary',
        'readonly': True,
    },
}

##code equivalence between 
## OpenERP and Postfinance
CODEEQUIV = {
    u'bvrpost' : u'28',
    u'bvrbank' : u'28',
    u'bvpost'  : u'22',
    u'bvbank'  : u'27', 
    u'00'      : u'00',
    u'97'      : u'97'
 
 }

    

class OPAELine(object):
    """OPAE Line contain in OPAE File"""
    
    currencies_handler = {}
    
    def __init__(self, cursor, uid, data, pool, payment_order, context=None):
        print cursor, uid, data, pool, payment_order, context
        self.sector = ''
        self.data = ''
        self.compo = {}
        ## Openerp Pooler
        self.pool = pool
        ## Psycopg cursor
        self.cursor = cursor
        ## OpenERP user id 
        self.uid = uid
        ## OpenERP wizard data
        self.wizdata = data
        # OpenERP current context 
        self.context = context and context.copy() or {}
        self.payment_order = payment_order
        

    ## @param self The object pointer.
    ## @payment the current payment order
    ## @line the current line
    def get_date(self, payment, line):
        """Return the right OPAE Line date"""
        if not line :
            return unicode(DateTime.today().strftime("%y%m%d"))
        to_return = DateTime.today()
        if payment.date_prefered == 'due' and line.ml_maturity_date :
            to_return = DateTime.strptime(line.ml_maturity_date, '%Y-%m-%d')
        if  payment.date_prefered == 'fixed' and payment.date_planned :
            to_return = DateTime.strptime(payment.date_planned, '%Y-%M-%d')
        if to_return < DateTime.today():
               raise wizard.except_wizard(
                                           _('Error'),
                                           _('Payment date must be at least today\n \
                                              Today used instead.')
                                          )
        return unicode(to_return.strftime("%y%m%d"))
        
        
    def set_communication(self, linebr):
        "Split line comment in 4 block of 35 chars"
        raw_comment = ''
        if linebr.communication and linebr.communication2:
            raw_comment = linebr.communication + ' ' + linebr.communication2
        else:
            raw_comment = linebr.communication 
        for i in xrange(0,140,35) :
            self.compo['communication_bloc_'+str(i/35+1)] = raw_comment[i:i+35]
            
    def set_address(self, prefix, addresses):
        for addr in addresses:
            if addr.type=='default':
                add_string = addr.street or u''
                add_string += u' '
                add_string += addr.street2 or u''
                add_string = add_string.replace(u"\n",u' ')
                self.compo[prefix+'_street'] = add_string[0:34]
                self.compo[prefix+'_npa'] = addr.zip or u''
                self.compo[prefix+'_city'] =  addr.city or u''
                
                
    def _create_control_sector(self):
        vals = self.compo
        opae_control_string =[] 
        ## chapter 4.2 secteur de controle -> identificateur de fichier
        opae_control_string.append(u'036')
        if not vals.get('line_date', False) :
            raise wizard.except_wizard(
                                        _('Error'), 
                                        _('Missing date planned  \n' \
                                        'for the payment order line: %s\n')
                                        )
     
        ## chapter 4.2 secteur de controle -> date decheance
        opae_control_string.append(vals['line_date'])
        ## chapter 4.2 secteur de controle -> reserve + element de commande fix val
        opae_control_string.append('0'* 5 + '1')
        ## chapter 4.2 secteur de controle -> No de compte de debit

        opae_control_string.append(vals['debit_account_number'].rjust(6,u'0'))
        ## chapter 4.2 secteur de controle -> N0 de compte de debit de tax
        opae_control_string.append(vals['debit_account_number'].rjust(6,u'0'))
        opae_control_string.append(vals['order_number'])


        try:
            print vals['transaction_type'], CODEEQUIV
            opae_control_string.append(CODEEQUIV[vals['transaction_type']])
            
        except Exception, e:
            raise wizard.except_wizard(_('Error'), _("Type doesn 't exists or isn 't supported yet."))

        transaction_id = unicode(vals['transaction_id'].rjust(6,u'0'))
        opae_control_string.append(transaction_id)
        opae_control_string.append(u'0' * 7)
        return (''.join(opae_control_string))[:50] 
        
    def _format_post_account(self, postnumber, lenght):
        numberpart = postnumber.split('-')
        if len(numberpart) != 3 or len(postnumber)>lenght:
            raise wizard.except_wizard(
                    ('Error'),
                    ('Post number account not in valid format ..-..-..')
                    )
        numberpart[1] = numberpart[1].rjust(lenght, u'0')
        return ''.join(numberpart)
        
    def escape_vals(self, indict={}):
        "Manage line encoding"
        for key in indict:
            string_in = indict[key]
            try:
                string_in = u''.join((c for c in unicodedata.normalize('NFD', string_in) \
                    if unicodedata.category(c) != 'Mn'))
                string_in.encode('ascii','ignore')
                indict[key] =  string_in
            except Exception, encode_err:
                print  key, encode_err
                return string_in    
        
    def _generate_dest_bank_string(self, vals):
        bank_string = []
        btype = vals['transaction_type']
        if btype == 'bvbank':
            if not vals['bic'] and not vals['iban']:
                raise wizard.except_wizard(
                                            _('Error'),
                                            _('Bic/swift number is requiered'+
                                            ' for bank %s if iban is not set'\
                                                %(vals['benef_bank_name']))
                                        )
            if vals['bic'] and (len(vals['bic']) < 8 or len(vals['bic']) >15)  :
                raise wizard.except_wizard(
                                            _('Error'),
                                            _('Error in bic.\nIf iban is present, just delete bic')
                                            )

            bank_string.append(vals['bic'].ljust(15, ' '))
        if btype in ('bvpost', 'bvbank'):    
            if btype == 'bvpost':
                if vals['postal_account_number']:
                    
                    bank_string.append(self._format_post_account(vals['postal_account_number'], 6))
                else:
                    raise wizard.except_wizard(
                                                _('Error'), 
                                                _('Missing postal account number')
                                            )

                bank_string.append(' '*6)

            if btype == 'bvbank' :
                if not vals['iban'] and not vals['postal_account_number']:
                    raise wizard.except_wizard(
                                            _('Error'),
                                            _('Missing IBAN or Postal account number')
                                        )

        
            if btype == 'bvbank' and not vals['iban']:
                if vals['postal_account_number']:
                    bank_string.append(self._format_post_account(vals['postal_account_number'], 6))
            else:
                if not vals['iban']:
                    raise wizard.except_wizard(
                                                     _('Error'), 
                                                     _('Iban missing')
                                                 )
                # error Iban lenght
                bank_string.append(vals['iban'].rjust(35,'0'))
        return u''.join(bank_string)
        
        
        
    def generate_string(self):
        vals = self.compo
        opae_string = []
        ##we transitarate the accuanted chars
        
        for key, string_in in vals.items() :
            try:
                string_in = u''.join((c for c in unicodedata.normalize('NFD', string_in) \
                    if unicodedata.category(c) != 'Mn'))
                string_in.encode('ascii','ignore')
                vals[key] = string_in
            except Exception, encode_err:
                print  key, encode_err
                vals[key] = string_in
                
        opae_string.append(self._create_control_sector())
        if vals['transaction_type']  == u'00':
            opae_string.append(u' '*650)
            return ''.join(opae_string)
        if vals['transaction_type'] in ('bvrpost', 'bvrbank', 'bvpost', 'bvbank'):
            opae_string.append(vals['deposit_currency'])
            ##we round and convert to cents
            amount = unicode(int(round(vals['deposit_amount']*100,2)))
            opae_string.append(amount.rjust(13, u'0'))
            opae_string.append(vals['bonification_currency'])


        if vals['deposit_currency'] in self.currencies_handler :
            self.currencies_handler[vals['deposit_currency']]['used'] += 1
            self.currencies_handler[vals['deposit_currency']]['total_amount'] += int(amount)

        else:
            self.currencies_handler[vals['deposit_currency']] = {'used':1,'total_amount':int(amount)}

        opae_string.append(vals['country_code'])
        opae_string.append(self._generate_dest_bank_string(vals))
        

        if vals['transaction_type'] in ('bvpost', 'bvbank'):
            opae_string.append(vals['dest_name'].rjust(35, ' ')[:35])
            opae_string.append(vals['dest_designation'].rjust(35, ' ')[:35])
            opae_string.append(vals['dest_street'].rjust(35, ' ')[:35])
            opae_string.append(vals['dest_npa'].ljust(10, ' ')[:10])
            opae_string.append(vals['dest_city'].ljust(25, ' ')[:25])
            if not vals['dest_npa']:
                raise wizard.except_wizard(_('Error'), _('No NPA'))
            if not vals['principal_npa']:
                raise wizard.except_wizard(_('Error'), _('No NPA'))
            opae_string.append(vals['benef_name'].rjust(35, ' ')[:35])
            opae_string.append(vals['benef_designation'].rjust(35, ' ')[:35])
            opae_string.append(vals['benef_street'].rjust(35, ' ')[:35])
            opae_string.append(vals['benef_npa'].ljust(10, ' '))
            opae_string.append(vals['dest_city'].rjust(25, ' ')[:25])
            opae_string.append(vals['communication_bloc_1'])
            opae_string.append(vals['communication_bloc_2'])
            opae_string.append(vals['communication_bloc_3'])
            opae_string.append(vals['communication_bloc_4'])
            opae_string.append(' '*4)
            opae_string.append(vals['principal_name'].rjust(35,' '))
            opae_string.append(vals['principal_designation'].rjust(35,' '))
            opae_string.append(vals['principal_street'].rjust(35,' ')[:35])
            opae_string.append(vals['principal_npa'].ljust(10,' '))
            opae_string.append(vals['principal_city'].rjust(25,' '))
            opae_string.append(' '*14)    
            
        if vals['transaction_type'] in ('bvrpost', 'bvrpost'):    
            opae_string.append(vals['modulo_11_digit'])
            if not vals['bvr_num']:
                raise wizard.except_wizard(
                                            _('Error'), 
                                            _('Please enter a BVR post account')
                                            )
            bvr_ad_num = vals['bvr_num'].split(u'-')

            if len(bvr_ad_num) == 1:
                if len(bvr_ad_num[0])!=5:
                    raise wizard.except_wizard(
                    _('Error'), 
                    _('invalid Post account number')
                )
                opae_string.append(bvr_ad_num.rjust(9,'0'))

            else :
                opae_string.append(self._format_post_account(vals['bvr_num'],6))
            opae_string.append(vals['reference'].rjust(27, '0'))
            opae_string.append(vals['sender_reference'])
            opae_string.append(' '*555)
        to_retunr = ''.join(opae_string)
        print '>>>>>>>>>>>>>>>>>>', to_retunr, opae_string
            ##To do test t return
            
        return to_retunr

        
        
class OPAE(object):
    "OPAE File representation"
    
    def __init__(self, cursor, uid, data, pool, context=None):
        ## Openerp Pooler
        self.pool = pool
        ## Psycopg cursor
        self.cursor = cursor
        ## OpenERP user id 
        self.uid = uid
        ## OpenERP wizard data
        self.wizdata = data
        # OpenERP current context 
        self.context = context
        #transaction id
        self.transaction = 0
        pay_id = data['ids']
        if isinstance(pay_id, list) :
            pay_id = pay_id[0]
        ## Current payment order
        self.payment_order = self.pool.get('payment.order').browse(
                                                                    cursor, 
                                                                    uid, 
                                                                    pay_id
                                                                   )
        ## OPAE string component                                                           
        self.compo =  {}
        ## Currency dict used for footer computation
        ## for more information look chapter 4.12 enregistrement total
        self.currencies = {}
        ## OPAE lines form of dict
        self.lines = []
        self.numers = {}
        ## Enregistrement de test a ne pas confondre avec secteur de controle
        if not self.payment_order.mode :
            raise wizard.except_wizard(_('Error'),
            _('No Payment mode define'))
        self.debit_account_number = self.payment_order.mode.\
                                    bank_id.bvr_number.replace(u'-',u'')
        ## header line representation                            
        self.headline = OPAELine(self.cursor, self.uid, self.wizdata, self.pool, self.payment_order, self.context)
        self.headline.compo['line_date'] = self.headline.get_date(self.payment_order, None)
        self.headline.compo['debit_account_number'] = self.debit_account_number
        self.headline.compo['bonification_currency'] = u''
        self.headline.compo['transaction_type'] = u'00'
        self.headline.compo['transaction_id'] = unicode(self.transaction)
        self.headline.compo['order_number'] = unicode(self.get_lines_order_num(self.headline.compo['line_date'], None))
        self.headline.compo['deposit_currency'] = self.payment_order.user_id.company_id.currency_id.code
        ## footer line representation                            
        self.footerline = OPAELine(self.cursor, self.uid, self.wizdata, self.pool, self.payment_order, self.context)
        self.footerline.compo['line_date'] = self.footerline.get_date(self.payment_order, None)
        self.footerline.compo['debit_account_number'] = self.debit_account_number
        self.footerline.compo['bonification_currency'] = u''
        self.footerline.compo['transaction_type'] = u'97'
        self.footerline.compo['transaction_id'] = unicode(self.transaction)
        self.footerline.compo['order_number'] = unicode(self.get_lines_order_num(self.footerline.compo['line_date'], None))
        self.footerline.compo['deposit_currency'] = self.payment_order.user_id.company_id.currency_id.code
        
        
        ### array of unicode string that will be used for joined
        ##  see PEP for details
        self.result_array = []
        
       
        
    def get_lines_order_num(self, date, currency):
        """Retrun next available order line from 0 to 99
           per currency rate"""
        key = (str(date), currency)
        if self.numers.has_key(key) :
            self.numers[key] += 1
            to_return =  self.numers[key]
            if to_return > 99 :
                raise wizard.except_wizard(_('Error'),
                    _('Order can not exced 99 lines per date and currency'))
            return unicode(to_return).rjust(2,'0')
        else :
            self.numers[key] = 1
            return '01'
                
        
    def create_opae_footer(self, line):
        opae_string = ''
        opae_string += line._create_control_sector()

        if len(line.currencies_handler) > 15:
            wizard.except_wizard(
                                    _('Error'),
                                    _('There are too many currencies used in this payment order.\nMaximum authorised by OPAE : 15\nCurrent payment order contains %s currencies') % (len(line.currencies_handler)))

        for currency in line.currencies_handler:
            opae_string += currency
            used = unicode(line.currencies_handler[currency]['used'])
            used = used.rjust(6, u'0')

            opae_string += used
            total_amount = unicode(line.currencies_handler[currency]['total_amount'])
            total_amount = total_amount.rjust(13,u'0')
            opae_string += total_amount

        for i in line.currencies_handler:
            opae_string += u'0' * 22

        opae_string += ' '*320    
        return opae_string


    
    def parse_payment_lines(self):
        """Compute the OPAE file output"""
        # 'Destinataire' and 'beneficiare' differences are
        # destinataire has his own post account
        # beneficiare has is account trought a bank that use a postal account
        # All term can be retrieved in 
        # Postfinance Tech spech "Enregistrement OPAE"
        self.transaction 
        for line in self.payment_order.line_ids:
            self.transaction += 1
            ## we have an unique id per OPAE line
            op_line = OPAELine(self.cursor, self.uid, self.wizdata, self.pool, self.payment_order, self.context)
            self.lines.append(op_line)
            ## we set limit execution date see chapter 4.2 date d'echeance
            op_line.compo['line_date'] = op_line.get_date(self.payment_order, line)
            ## we set the destination account 
            ##  see chapter 4.2 numero de compte de débit
            op_line.compo['debit_account_number'] = self.payment_order.mode.\
                                    bank_id.bvr_number.replace(u'-',u'')
            ## chapter 4.2 numero de compte de debit des taxes
            op_line.compo['debit_tax_account_number'] = op_line.compo['debit_account_number']
            op_line.compo['currency'] = line.currency.code
            ## We define line order number chapter 4.2 numero d'ordre
            op_line.compo['order_number'] = unicode(self.get_lines_order_num(
                                                  op_line.compo['line_date'],
                                                  line.currency.code
                                                ))
            state = line.bank_id.state or self.payment_order.mode.bank_id.state
            ## chapter 4.2 genre de transaction
            op_line.compo['transaction_type'] = state
            ## chapter 4.2 no courant de transaction
            op_line.compo['transaction_id'] = unicode(self.transaction)
            ## chapter 4.x Code ISO Monnaie de Depot 
            op_line.compo['deposit_currency'] = line.currency.code
            ## chap 4.x montant du depot
            op_line.compo['deposit_amount'] = line.amount_currency
            ## chap 4.x Code ISO Monnaie de bonnification
            op_line.compo['bonification_currency'] = unicode(line.currency.code)
            ## chap 4.x code ISO pays
            op_line.compo['country_code'] = self.payment_order.user_id.company_id.\
                partner_id.country.code
            ## chapter 4.x No de compte postal du destinataire
            op_line.compo['postal_account_number'] = line.bank_id.post_number or u''
            ## chapter 4.x No IBAN du destinaire/beneficiaire
            op_line.compo['iban'] = line.bank_id.iban or u''
            ## chapter 4.x No IBAN du destinaire/beneficiaire
            ## iban
            op_line.compo['iban' ] =  op_line.compo['iban'].upper()
            ## address management
            if state in ('bvpost', 'bvrpost') :
                if line.partner_id:
                    partner = line.partner_id
                    op_line.compo['benef_name'] = partner.name
                    op_line.set_address('benef', partner.address)
                op_line.compo['dest_name'] =  op_line.compo['benef_name']
                op_line.compo['dest_street'] = op_line.compo['benef_street']
                op_line.compo['dest_npa'] = op_line.compo['benef_npa']
                op_line.compo['dest_city'] = op_line.compo['benef_city']
                op_line.compo['dest_designation'] = u''
                op_line.compo['benef_designation'] = u''
            else :
                op_line.compo['dest_npa'] = line.bank_id.bank and line.bank_id.bank.zip or ''
                op_line.compo['dest_name'] = line.bank_id.bank and line.bank_id.bank.name or ''
                op_line.compo['dest_designation'] = ''
                op_line.compo['benef_designation'] = ''
                op_line.compo['dest_street'] = line.bank_id.bank and line.bank_id.bank.street or ''
                op_line.compo['dest_city'] = line.bank_id.bank and line.bank_id.bank.city or '' 
                op_line.compo['benef_name'] = line.bank_id.owner_name or u''
                op_line.compo['benef_street'] =  line.bank_id.street or u''
                op_line.compo['benef_npa'] = line.bank_id.zip or u''
                op_line.compo['benef_city'] = line.bank_id.city or u''
                
                    
            op_line.set_communication(line)
            ## principal correspond to the source of payment
            op_line.compo['principal_name'] = u''
            op_line.compo['principal_street'] = u''
            op_line.compo['principal_npa'] = u''
            op_line.compo['principal_city'] = u''
            if self.payment_order.mode.bank_id.partner_id :
                partner = self.payment_order.mode.bank_id.partner_id
                op_line.compo['principal_name'] = partner.name
                op_line.set_address('principal', partner.address)
            op_line.compo['principal_designation'] = u''
            op_line.compo['bic'] = line.bank_id.bank and line.bank_id.bank.bic or ''
            ##final bebficiary bank            

            op_line.compo['modulo_11_digit'] = u'  '
            op_line.compo['bvr_num'] = self.payment_order.mode.bank_id.bvr_number or ''
            op_line.compo['reference'] = line.communication
            op_line.compo['sender_reference'] = u' ' * 35
        
    def compute(self):
        """Compute the OPAE file output"""
        self.result_array.append(self.headline.generate_string())  
        for parsed_line in self.lines :
             self.result_array.append(parsed_line.generate_string())
        self.result_array.append(self.create_opae_footer(self.footerline))
        print self.result_array
        return  "\n".join(self.result_array)


def _prepare_opae(obj, cursor, uid, data, context):
    pool = pooler.get_pool(cursor.dbname)
    opae = OPAE(cursor, uid, data, pool, context)
    opae.parse_payment_lines()
    res = opae.compute()    
    return {'opae': base64.encodestring(res)}

 


class WizardOpaeCreate(wizard.interface):
    states = {
        'init' : {
            'actions' : [_prepare_opae],
            'result' : {'type' : 'form',
                'arch' : FORM,
                'fields' : FIELDS,
                'state' : [('end', 'OK', 'gtk-ok', True)]
            }
        },
    }

WizardOpaeCreate('account.opae_create')