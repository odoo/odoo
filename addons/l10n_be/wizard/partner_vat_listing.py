# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
import datetime
import base64

import wizard
import pooler
from tools.translate import _
import tools
from osv import fields, osv

class vat_listing_clients(osv.osv_memory):
    _name = 'vat.listing.clients'
    _columns = {
        'name': fields.char('Cleint Name', size=64),
        'vat': fields.char('VAT', size=64),
        'country': fields.char('Country', size=64),
        'amount': fields.float('Amount'),
        'turnover': fields.float('Turnover'),
                }

vat_listing_clients()

form = """<?xml version="1.0"?>
<form string="Select Fiscal Year">
    <label string="This wizard will create an XML file for Vat details and total invoiced amounts per partner."  colspan="4"/>
    <newline/>
    <field name="fyear" />
    <newline/>
    <field name="mand_id" help="Should be provided when subscription of INTERVAT service is done"/>
    <newline/>
    <field name="limit_amount" help="Limit under which the partners will not be included into the listing"/>
    <newline/>
    <field name="test_xml" help="Set the XML output as test file"/>
</form>"""

fields = {
    'fyear': {'string': 'Fiscal Year', 'type': 'many2one', 'relation': 'account.fiscalyear', 'required': True,},
    'mand_id':{'string':'MandataireId','type':'char','size':'30','required': True,},
    'limit_amount':{'string':'Limit Amount','type':'integer','required': True, },
    'test_xml': {'string':'Test XML file', 'type':'boolean', },
   }

client_form = """<?xml version="1.0"?>
<form string="Select Fiscal Year">
    <label string="You can remove clients/partners which you do not want in exported xml file"  colspan="4"/>
    <separator string="Clients" colspan="4"/>
    <field name="partners" colspan="4" width="600" height="250" widget="one2many" nolabel="1"/>
</form>"""

client_fields = {
    'partners': {'string': 'Cleints', 'type': 'many2many', 'relation': 'vat.listing.clients', 'required': False, 'help': 'You can remove clients/partners which you do not want to show in xml file'},
                 }

msg_form = """<?xml version="1.0"?>
<form string="Notification">
    <separator string="XML File has been Created."  colspan="4"/>
    <field name="msg" colspan="4" nolabel="1"/>
    <field name="name"/>
    <newline/>
    <field name="file_save" />
</form>"""

msg_fields = {
  'name': {'string': 'File name', 'type':'char', 'size':'32'},
  'msg': {'string':'File created', 'type':'text', 'size':'100','readonly':True},
  'file_save':{'string': 'Save File',
        'type': 'binary',
        'readonly': True,},
}

class wizard_vat(wizard.interface):

    def _get_partner(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        period_ids = pool.get('account.period').search(cr, uid, [('fiscalyear_id', '=', data['form']['fyear'])])
        period = "("+','.join(map(lambda x: str(x), period_ids)) +")"

        p_id_list = pool.get('res.partner').search(cr,uid,[('vat_subjected','!=',False)])
        if not p_id_list:
             raise wizard.except_wizard(_('Data Insufficient!'),_('No partner has a VAT Number asociated with him.'))
        partners = []
        records = []
        for obj_partner in pool.get('res.partner').browse(cr, uid, p_id_list):
            record = {} # this holds record per partner

            #This listing is only for customers located in belgium, that's the
            #reason why we skip all the partners that haven't their
            #(or one of their) default address(es) located in Belgium.
            go_ahead = False
            for ads in obj_partner.address:
                if ads.type == 'default' and (ads.country_id and ads.country_id.code == 'BE'):
                    go_ahead = True
                    break
            if not go_ahead:
                continue
            query = 'select b.code,sum(credit)-sum(debit) from account_move_line l left join account_account a on (l.account_id=a.id) left join account_account_type b on (a.user_type=b.id) where b.code in ('"'produit'"','"'tax'"') and l.partner_id='+str(obj_partner.id)+' and l.period_id in '+period+' group by b.code'
            cr.execute(query)
            line_info = cr.fetchall()
            if not line_info:
                continue

            record['vat'] = obj_partner.vat

            #it seems that this listing is only for belgian customers
            record['country'] = 'BE'
            #...deprecated...
            #~addr = pool.get('res.partner').address_get(cr, uid, [obj_partner.id], ['invoice'])

            #~ if addr.get('invoice',False):
                #~ads=pool.get('res.partner.address').browse(cr,uid,[addr['invoice']])[0]

                #~ if ads.country_id:
                    #~ record.append(ads.country_id.code)
                #~ else:
                    #~ error_message.append('Data Insufficient! : '+ 'The Partner "'+obj_partner.name + '"'' has no country associated with its Invoice address!')

            #~ if len(record)<2:
                #~ record.append('')
                #~ error_message.append('Data Insufficient! : '+ 'The Partner "'+obj_partner.name + '"'' has no Invoice address!')

            record['amount'] = 0
            record['turnover'] = 0
            record['name'] = obj_partner.name

            for item in line_info:
                if item[0]=='produit':
                    record['turnover'] += item[1]
                else:
                    record['amount'] += item[1]
            id_client = pool.get('vat.listing.clients').create(cr, uid, record)
            partners.append(id_client)
            records.append(record)

        return {'partners':partners}

    def _create_xml(self, cr, uid, data, context):
        datas=[]
        pool = pooler.get_pool(cr.dbname)
        seq_controlref = pool.get('ir.sequence').get(cr, uid,'controlref')
        seq_declarantnum = pool.get('ir.sequence').get(cr, uid,'declarantnum')
        obj_cmpny = pool.get('res.users').browse(cr, uid, uid).company_id
        company_vat = obj_cmpny.partner_id.vat
        if not company_vat:
            raise wizard.except_wizard(_('Data Insufficient'),_('No VAT Number Associated with Main Company!'))

        cref = company_vat + seq_controlref
        dnum = cref + seq_declarantnum

        obj_year=pool.get('account.fiscalyear').browse(cr,uid,data['form']['fyear'])
        street = zip_city = country = ''
        addr = pool.get('res.partner').address_get(cr, uid, [obj_cmpny.partner_id.id], ['invoice'])
        if addr.get('invoice',False):
            ads=pool.get('res.partner.address').browse(cr,uid,[addr['invoice']])[0]

            zip_city = pool.get('res.partner.address').get_city(cr,uid,ads.id)
            if not zip_city:
                zip_city = ''
            if ads.street:
                street = ads.street
            if ads.street2:
                street += ads.street2
            if ads.country_id:
                country = ads.country_id.code

        sender_date = time.strftime('%Y-%m-%d')

        data_file = '<?xml version="1.0"?>\n<VatList xmlns="http://www.minfin.fgov.be/VatList" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.minfin.fgov.be/VatList VatList.xml" RecipientId="VAT-ADMIN" SenderId="'+ str(company_vat) + '"'
        data_file +=' ControlRef="'+ cref + '" MandataireId="'+ tools.ustr(data['form']['mand_id']) + '" SenderDate="'+ str(sender_date)+ '"'
        if data['form']['test_xml']:
            data_file += ' Test="0"'
        data_file += ' VersionTech="1.2">'
        data_file += '\n<AgentRepr DecNumber="1">\n\t<CompanyInfo>\n\t\t<VATNum>'+str(company_vat)+'</VATNum>\n\t\t<Name>'+tools.ustr(obj_cmpny.name)+'</Name>\n\t\t<Street>'+ tools.ustr(street) +'</Street>\n\t\t<CityAndZipCode>'+ tools.ustr(zip_city) +'</CityAndZipCode>'
        data_file += '\n\t\t<Country>'+ tools.ustr(country) +'</Country>\n\t</CompanyInfo>\n</AgentRepr>'
        data_comp = '\n<CompanyInfo>\n\t<VATNum>'+str(company_vat)+'</VATNum>\n\t<Name>'+tools.ustr(obj_cmpny.name)+'</Name>\n\t<Street>'+ tools.ustr(street) +'</Street>\n\t<CityAndZipCode>'+ tools.ustr(zip_city) +'</CityAndZipCode>\n\t<Country>'+ tools.ustr(country) +'</Country>\n</CompanyInfo>'
        data_period = '\n<Period>'+ tools.ustr(obj_year.date_stop[:4]) +'</Period>'
        error_message = []

        for partner in data['form']['partners']:
            if isinstance(partner, list) and partner:
                datas.append(partner[2])
            else:
                client_data = pool.get('vat.listing.clients').read(cr, uid, partner, context=context)
                datas.append(client_data)

        seq=0
        data_clientinfo=''
        sum_tax=0.00
        sum_turnover=0.00
        if len(error_message):
            data['form']['msg']='Exception : \n' +'-'*50+'\n'+ '\n'.join(error_message)
            return data['form']
        for line in datas:
            if not line:
                continue
            if line['turnover'] < data['form']['limit_amount']:
                continue
            seq +=1
            sum_tax +=line['amount']
            sum_turnover +=line['turnover']
            data_clientinfo +='\n<ClientList SequenceNum="'+str(seq)+'">\n\t<CompanyInfo>\n\t\t<VATNum>'+line['vat'] +'</VATNum>\n\t\t<Country>'+tools.ustr(line['country']) +'</Country>\n\t</CompanyInfo>\n\t<Amount>'+str(int(line['amount'] * 100)) +'</Amount>\n\t<TurnOver>'+str(int(line['turnover'] * 100)) +'</TurnOver>\n</ClientList>'

        data_decl ='\n<DeclarantList SequenceNum="1" DeclarantNum="'+ dnum + '" ClientNbr="'+ str(seq) +'" TurnOverSum="'+ str(int(sum_turnover * 100)) +'" TaxSum="'+ str(int(sum_tax * 100)) +'" />'
        data_file += tools.ustr(data_decl) + tools.ustr(data_comp) + tools.ustr(data_period) + tools.ustr(data_clientinfo) + '\n</VatList>'

        data['form']['msg'] = 'Save the File with '".xml"' extension.'
        data['form']['file_save'] = base64.encodestring(data_file.encode('utf8'))
        data['form']['name'] = 'vat_list.xml'
        return data['form']

    states = {
        'init': {
            'actions': [],
            'result': {'type':'form', 'arch':form, 'fields':fields, 'state':[('end','Cancel'),('go_step','View Clients')]},
        },
        'go_step': {
            'actions': [_get_partner],
            'result': {'type':'form', 'arch':client_form, 'fields':client_fields, 'state':[('end','Cancel'),('go','Create XML')]},
        },
        'go': {
            'actions': [_create_xml],
            'result': {'type':'form', 'arch':msg_form, 'fields':msg_fields, 'state':[('end','Ok')]},
        }

    }

wizard_vat('list.vat.detail')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: