# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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

from tools.translate import _

form_fyear = """<?xml version="1.0"?>
<form string="Select Period">
    <field name="period" />
    <field name="ask_resitution"/>
    <field name="ask_payment"/>
    <field name="client_nihil"/>
</form>"""

fields_fyear = {
    'period': {'string': 'Period', 'type': 'many2one', 'relation': 'account.period', 'required': True,},
    'ask_resitution': {'type': 'boolean', 'string': 'Ask Restitution',},
    'ask_payment': {'type': 'boolean', 'string': 'Ask Payment',},
    'client_nihil': {'type': 'boolean', 'string': 'Last Declaration of Entreprise', 'help': 'Thick this case only if it concerns only the last statement on the civil or cessation of activity'},
}

form = """<?xml version="1.0"?>
<form string="Notification">
     <separator string="XML Flie has been Created."  colspan="4"/>
     <field name="msg" colspan="4" nolabel="1"/>
     <field name="file_save" />
</form>"""

fields = {
    'msg': {'string':'File created', 'type':'text', 'size':'100','readonly':True},
    'file_save':{'string': 'Save File',
        'type': 'binary',
        'readonly': True,},
}


class wizard_vat_declaration(wizard.interface):

    def _create_xml(self, cr, uid, data, context):
        list_of_tags=['00','01','02','03','44','45','46','47','48','49','54','55','56','57','59','61','62','63','64','71','81','82','83','84','85','86','87','88','91']
        pool_obj = pooler.get_pool(cr.dbname)
        #obj_company = pool_obj.get('res.company').browse(cr,uid,1)
        obj_company = pooler.get_pool(cr.dbname).get('res.users').browse(cr, uid, uid).company_id
        user_cmpny = obj_company.name
        vat_no=obj_company.partner_id.vat
        if not vat_no:
            raise wizard.except_wizard(_('Data Insufficient'),_('No VAT Number Associated with Main Company!'))

        tax_ids = pool_obj.get('account.tax.code').search(cr,uid,[])
        ctx = context.copy()
        ctx['period_id'] = data['form']['period'] #added context here
        tax_info = pool_obj.get('account.tax.code').read(cr,uid,tax_ids,['code','sum_period'],context=ctx)

        address = post_code = city = country_code = ''

        city, post_code, address, country_code = pooler.get_pool(cr.dbname).get('res.company')._get_default_ad(obj_company.partner_id.address)

        obj_fyear = pool_obj.get('account.fiscalyear')
        year_id = obj_fyear.find(cr, uid)
        
        account_period=pool_obj.get('account.period').browse(cr, uid, data['form']['period'])
        period_code = account_period.code

        send_ref = str(obj_company.partner_id.id) + str(account_period.date_start[5:7]) + str(account_period.date_stop[:4])

        data_of_file='<?xml version="1.0"?>\n<VATSENDING xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="MultiDeclarationTVA-NoSignature-16.xml">'
        data_of_file +='\n\t<DECLARER>\n\t\t<VATNUMBER>'+str(vat_no)+'</VATNUMBER>\n\t\t<NAME>'+ obj_company.name +'</NAME>\n\t\t<ADDRESS>'+address+'</ADDRESS>'
        data_of_file +='\n\t\t<POSTCODE>'+post_code+'</POSTCODE>\n\t\t<CITY>'+city+'</CITY>\n\t\t<COUNTRY>'+country_code+'</COUNTRY>\n\t\t<SENDINGREFERENCE>'+send_ref+'</SENDINGREFERENCE>\n\t</DECLARER>'
        data_of_file +='\n\t<VATRECORD>\n\t\t<RECNUM>1</RECNUM>\n\t\t<VATNUMBER>'+str(vat_no[2:])+'</VATNUMBER>\n\t\t<DPERIODE>\n\t\t\t'

        starting_month = account_period.date_start[5:7]
        ending_month = account_period.date_stop[5:7]
        if starting_month != ending_month:
            #starting month and ending month of selected period are not the same 
            #it means that the accounting isn't based on periods of 1 month but on quarters
            quarter = str(((int(starting_month) - 1) / 3) + 1)
            data_of_file += '<QUARTER>'+quarter+'</QUARTER>\n\t\t\t'
        else:
            data_of_file += '<MONTH>'+starting_month+'</MONTH>\n\t\t\t'
        data_of_file += '<YEAR>' + str(account_period.date_stop[:4]) + '</YEAR>\n\t\t</DPERIODE>\n\t\t<ASK RESTITUTION="NO" PAYMENT="NO"/>'
        data_of_file += '\n\t\t<ClientListingNihil>'+ (data['form']['client_nihil'] and 'YES' or 'NO') +'</ClientListingNihil>'
        data_of_file +='\n\t\t<DATA>\n\t\t\t<DATA_ELEM>'

        for item in tax_info:
            if item['code'] == '91' and ending_month != 12:
                #the tax code 91 can only be send for the declaration of December
                continue
            if item['code']:
                if item['code'] == '71-72':
                    item['code']='71'
                if item['code'] in list_of_tags:
                    data_of_file +='\n\t\t\t\t<D'+str(int(item['code'])) +'>' + str(abs(int(item['sum_period']*100))) +  '</D'+str(int(item['code'])) +'>'

        data_of_file +='\n\t\t\t</DATA_ELEM>\n\t\t</DATA>\n\t</VATRECORD>\n</VATSENDING>'
        data['form']['msg']='Save the File with '".xml"' extension.'
        data['form']['file_save'] = base64.encodestring(data_of_file.encode('utf8'))
        return data['form']


    states = {
        'init': {
            'actions': [],
            'result': {'type':'form', 'arch':form_fyear, 'fields':fields_fyear, 'state':[('end','Cancel'),('go','Create XML')]},
        },
        'go': {
            'actions': [_create_xml],
            'result': {'type':'form', 'arch':form, 'fields':fields, 'state':[('end','Ok')]},
        }
    }

wizard_vat_declaration('wizard.account.xml.vat.declaration')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
