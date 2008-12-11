# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
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
import wizard
import time
import datetime
import pooler
import base64

form = """<?xml version="1.0"?>
<form string="Select Fiscal Year">
    <label string="This wizard will create an XML file for Vat details and total invoiced amounts per partner."  colspan="4"/>
    <newline/>
    <field name="fyear" />
    <newline/>
    <field name="mand_id" help="Should be provided when subcription of INTERVAT service is done"/>
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
msg_form = """<?xml version="1.0"?>
<form string="Notification">
     <separator string="XML File has been Created."  colspan="4"/>
     <field name="msg" colspan="4" nolabel="1"/>
     <field name="file_save" />
</form>"""

msg_fields = {
  'msg': {'string':'File created', 'type':'text', 'size':'100','readonly':True},
  'file_save':{'string': 'Save File',
        'type': 'binary',
        'readonly': True,},
}

class wizard_vat(wizard.interface):

    def _create_xml(self, cr, uid, data, context):
        datas=[]
        # now wizard will use user->company instead of directly company from res.company

        seq_controlref = pooler.get_pool(cr.dbname).get('ir.sequence').get(cr, uid,'controlref')
        seq_declarantnum = pooler.get_pool(cr.dbname).get('ir.sequence').get(cr, uid,'declarantnum')
        obj_cmpny = pooler.get_pool(cr.dbname).get('res.users').browse(cr, uid, uid).company_id
        company_vat = obj_cmpny.partner_id.vat
        if not company_vat: #if not vat_company:
            raise wizard.except_wizard('Data Insufficient','No VAT Number Associated with Main Company!')

        cref = company_vat + seq_controlref
        dnum = cref + seq_declarantnum
#        obj_company=pooler.get_pool(cr.dbname).get('res.company').browse(cr,uid,1)
#        vat_company=obj_company.partner_id.vat

#TODO:  can be improved if we replace this test => add a new field on res_partner for cases when a partner has a number and is not subjected to the VAT... have to see if this situation could happen
        p_id_list=pooler.get_pool(cr.dbname).get('res.partner').search(cr,uid,[('vat','!=',False)])

        if not p_id_list:
             raise wizard.except_wizard('Data Insufficient!','No partner has a VAT Number asociated with him.')
        obj_year=pooler.get_pool(cr.dbname).get('account.fiscalyear').browse(cr,uid,data['form']['fyear'])
        period="to_date('" + str(obj_year.date_start) + "','yyyy-mm-dd') and to_date('" + str(obj_year.date_stop) +"','yyyy-mm-dd')"

        street=zip_city=country=''
        if not obj_cmpny.partner_id.address:
                street=zip_city=country=''

        for ads in obj_cmpny.partner_id.address:
                if ads.type=='default':
                    if ads.zip_id:
                        zip_city=pooler.get_pool(cr.dbname).get('res.partner.zip').name_get(cr,uid,[ads.zip_id.id])[0][1]
                    if ads.street:
                        street=ads.street
                    if ads.street2:
                        street +=ads.street2
                    if ads.country_id:
                        country=ads.country_id.code


        sender_date=time.strftime('%Y-%m-%d')
        data_file='<?xml version="1.0"?>\n<VatList xmlns="http://www.minfin.fgov.be/VatList" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.minfin.fgov.be/VatList VatList.xml" RecipientId="VAT-ADMIN" SenderId="'+ str(company_vat) + '"'
        data_file +=' ControlRef="'+ cref + '" MandataireId="'+ data['form']['mand_id'] + '" SenderDate="'+ str(sender_date)+ '"'
        if data['form']['test_xml']:
            data_file += 'Test="0"'
        data_file += ' VersionTech="1.2">'
        data_file +='\n<AgentRepr DecNumber="1">\n\t<CompanyInfo>\n\t\t<VATNum>'+str(company_vat)+'</VATNum>\n\t\t<Name>'+str(obj_cmpny.name)+'</Name>\n\t\t<Street>'+ str(street) +'</Street>\n\t\t<CityAndZipCode>'+ str(zip_city) +'</CityAndZipCode>'
        data_file +='\n\t\t<Country>'+ str(country) +'</Country>\n\t</CompanyInfo>\n</AgentRepr>'
        data_comp ='\n<CompanyInfo>\n\t<VATNum>'+str(company_vat)+'</VATNum>\n\t<Name>'+str(obj_cmpny.name)+'</Name>\n\t<Street>'+ str(street) +'</Street>\n\t<CityAndZipCode>'+ str(zip_city) +'</CityAndZipCode>\n\t<Country>'+ str(country) +'</Country>\n</CompanyInfo>'
        data_period ='\n<Period>'+ str(obj_year.name[-4:]) +'</Period>'

        for p_id in p_id_list:
            record=[] # this holds record per partner
            obj_partner=pooler.get_pool(cr.dbname).get('res.partner').browse(cr,uid,p_id)
            cr.execute('select b.code,sum(credit)-sum(debit) from account_move_line l left join account_account a on (l.account_id=a.id) left join account_account_type b on (a.user_type=b.id) where b.code in ('"'produit'"','"'tax'"') and l.partner_id=%%s and l.date between %s group by a.type' % (period,), (p_id,))
            line_info=cr.fetchall()
            if not line_info:
                continue

            record.append(obj_partner.vat)
            for ads in obj_partner.address:
                if ads.type=='default':
                    if ads.country_id:
                        record.append(ads.country_id.code)
                    else:
                        raise wizard.except_wizard('Data Insufficient!', 'The Partner "'+obj_partner.name + '"'' has no country associated with its default type address!')
                else:
                    raise wizard.except_wizard('Data Insufficient!', 'The Partner "'+obj_partner.name + '"'' has no default type address!')
            if len(line_info)==1:
                if line_info[0][0]=='produit':
                       record.append(0.00)
                       record.append(line_info[0][1])
                else:
                       record.append(line_info[0][1])
                       record.append(0.00)
            else:
                for item in line_info:
                    record.append(item[1])
            datas.append(record)

        seq=0
        data_clientinfo=''
        sum_tax=0.00
        sum_turnover=0.00
        for line in datas:
            if line[3]< data['form']['limit_amount']:
                continue
            seq +=1
            sum_tax +=line[2]
            sum_turnover +=line[3]
            data_clientinfo +='\n<ClientList SequenceNum="'+str(seq)+'">\n\t<CompanyInfo>\n\t\t<VATNum>'+line[0] +'</VATNum>\n\t\t<Country>'+line[1] +'</Country>\n\t</CompanyInfo>\n\t<Amount>'+str(int(line[2] * 100)) +'</Amount>\n\t<TurnOver>'+str(int(line[3] * 100)) +'</TurnOver>\n</ClientList>'

        data_decl ='\n<DeclarantList SequenceNum="1" DeclarantNum="'+ dnum + '" ClientNbr="'+ str(seq) +'" TurnOverSum="'+ str(int(sum_turnover * 100)) +'" TaxSum="'+ str(int(sum_tax * 100)) +'" />'
        data_file += str(data_decl) + str(data_comp) + str(data_period) + str(data_clientinfo) + '\n</VatList>'

        data['form']['msg']='Save the File with '".xml"' extension.'
        data['form']['file_save']=base64.encodestring(data_file)
        return data['form']

    states = {
        'init': {
            'actions': [],
            'result': {'type':'form', 'arch':form, 'fields':fields, 'state':[('end','Cancel'),('go','Create XML')]},
        },
        'go': {
            'actions': [_create_xml],
            'result': {'type':'form', 'arch':msg_form, 'fields':msg_fields, 'state':[('end','Ok')]},
        }

    }

wizard_vat('list.vat.detail')
