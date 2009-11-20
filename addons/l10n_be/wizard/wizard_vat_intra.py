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

import wizard
import time
import datetime
import pooler
import base64

form_intra = """<?xml version="1.0"?>
<form string="Partner VAT Intra">
    <notebook>
    <page string="General Information">
    <label string="This wizard will create an XML file for Vat Intra" colspan="4"/>
    <newline/>
    <field name="fyear" />
    <newline/>
    <field name="mand_id" help="This identifies the representative of the sending company. This is a string of 14 characters"/>
    <newline/>
    <field name="trimester" help="it will be the first digit of period" />
    <newline/>
    <field name="test_xml" help="Set the XML output as test file"/>
    </page>
    <page string="European Countries">
    <field name="country_ids" colspan="4" nolabel="1" />
    </page>
    </notebook>
</form>"""
fields_intra = {
    'trimester': {'string': 'Trimester Number', 'type': 'selection', 'selection':[
            ('1','Jan/Feb/Mar'),
            ('2','Apr/May/Jun'),
            ('3','Jul/Aug/Sep'),
            ('4','Oct/Nov/Dec')], 'required': True},
    'test_xml': {'string':'Test XML file', 'type':'boolean'},
    'mand_id':{'string':'MandataireId','type':'char','size':'14','required': True},
    'fyear': {'string': 'Fiscal Year', 'type': 'many2one', 'relation': 'account.fiscalyear', 'required': True},
    'country_ids': {
        'string': 'European Countries',
        'type': 'many2many',
        'relation': 'res.country',
        'required': False
    },
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

class parter_vat_intra(wizard.interface):

    def _get_europe_country(self, cr, uid, data, context):
        country_ids = pooler.get_pool(cr.dbname).get('res.country').search(cr, uid, [('code', 'in', ['AT', 'BG', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'DE', 'GR', 'HU', 'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'NL', 'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE', 'GB'])])
        return {'country_ids': country_ids}

    def _create_xml(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        data_cmpny = pool.get('res.users').browse(cr, uid, uid).company_id
        data_fiscal = pool.get('account.fiscalyear').browse(cr,uid,data['form']['fyear'])
        company_vat = data_cmpny.partner_id.vat

        if not company_vat:
            raise wizard.except_wizard('Data Insufficient','No VAT Number Associated with Main Company!')

        seq_controlref = pool.get('ir.sequence').get(cr, uid,'controlref')
        seq_declarantnum = pool.get('ir.sequence').get(cr, uid,'declarantnum')
        cref = company_vat + seq_controlref
        dnum = cref + seq_declarantnum
        if len(data_fiscal.date_start.split('-')[0]) < 4:
            raise wizard.except_wizard('Data Insufficient','Trimester year should be length of 4 digits!')
        period_trimester = data['form']['trimester'] + data_fiscal.date_start.split('-')[0]

        street = zip_city = country = ''
        addr = pool.get('res.partner').address_get(cr, uid, [data_cmpny.partner_id.id], ['invoice'])
        if addr.get('invoice',False):
            ads = pool.get('res.partner.address').browse(cr,uid,[addr['invoice']])[0]
            zip_city = (ads.city or '') + ' ' + (ads.zip or '')
            if zip_city== ' ':
                zip_city = ''
            if ads.street:
                street = ads.street
            if ads.street2:
                street += ' '
                street += ads.street2
            if ads.country_id:
                country = ads.country_id.code

        sender_date = time.strftime('%Y-%m-%d')
        data_file = '<?xml version="1.0"?>\n<VatIntra xmlns="http://www.minfin.fgov.be/VatIntra" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" RecipientId="VAT-ADMIN" SenderId="' + str(company_vat) + '"'
        data_file +=' ControlRef="' + cref + '" MandataireId="' + data['form']['mand_id'] + '" SenderDate="'+ str(sender_date)+ '"'
        if data['form']['test_xml']:
            data_file += ' Test="1"'
        data_file += ' VersionTech="1.2">'
        data_file +='\n\t<AgentRepr DecNumber="1">\n\t\t<CompanyInfo>\n\t\t\t<VATNum>' + str(company_vat)+'</VATNum>\n\t\t\t<Name>'+str(data_cmpny.name)+'</Name>\n\t\t\t<Street>'+ str(street) +'</Street>\n\t\t\t<CityAndZipCode>'+ str(zip_city) +'</CityAndZipCode>'
        data_file +='\n\t\t\t<Country>' + str(country) +'</Country>\n\t\t</CompanyInfo>\n\t</AgentRepr>'

        data_comp ='\n\t\t<CompanyInfo>\n\t\t\t<VATNum>'+str(company_vat)+'</VATNum>\n\t\t\t<Name>'+str(data_cmpny.name)+'</Name>\n\t\t\t<Street>'+ str(street) +'</Street>\n\t\t\t<CityAndZipCode>'+ str(zip_city) +'</CityAndZipCode>\n\t\t\t<Country>'+ str(country) +'</Country>\n\t\t</CompanyInfo>'
        data_period = '\n\t\t<Period>'+ str(period_trimester) +'</Period>' #trimester

        error_message = []
        seq = 0
        amount_sum = 0
        p_id_list = pool.get('res.partner').search(cr,uid,[('vat','!=',False)])
        if not p_id_list:
            raise wizard.except_wizard('Data Insufficient!','No partner has a VAT Number asociated with him.')

        nb_period = len(data_fiscal.period_ids)
        fiscal_periods = data_fiscal.period_ids

        if data['form']['trimester'] == '1':
            if nb_period == 12:
                start_date = fiscal_periods[0].date_start
                end_date = fiscal_periods[2].date_stop
            elif nb_period == 4:
                start_date = fiscal_periods[0].date_start
                end_date = fiscal_periods[0].date_stop
        elif data['form']['trimester'] == '2':
            if nb_period == 12:
                start_date = fiscal_periods[3].date_start
                end_date = fiscal_periods[5].date_stop
            elif nb_period == 4:
                start_date = fiscal_periods[1].date_start
                end_date = fiscal_periods[1].date_stop
        elif data['form']['trimester'] == '3':
            if nb_period == 12:
                start_date = fiscal_periods[6].date_start
                end_date = fiscal_periods[8].date_stop
            elif nb_period == 4:
                start_date = fiscal_periods[2].date_start
                end_date = fiscal_periods[2].date_stop
        elif data['form']['trimester'] == '4':
            if nb_period == 12:
                start_date = fiscal_periods[9].date_start
                end_date = fiscal_periods[11].date_stop
            elif nb_period == 4:
                start_date = fiscal_periods[3].date_start
                end_date = fiscal_periods[3].date_stop

        period = "to_date('" + str(start_date) + "','yyyy-mm-dd') and to_date('" + str(end_date) +"','yyyy-mm-dd')"
        record = {}

        for p_id in p_id_list:
            list_partner = []
            partner = pool.get('res.partner').browse(cr, uid, p_id)
            go_ahead = False
            country_code = ''
            for ads in partner.address:
                if ads.type == 'default' and (ads.country_id and ads.country_id.id in data['form']['country_ids'][0][2]):
                    go_ahead = True
                    country_code = ads.country_id.code
                    break
            if not go_ahead:
                continue

            cr.execute('select sum(debit)-sum(credit) as amount from account_move_line l left join account_account a on (l.account_id=a.id) where a.type in ('"'receivable'"') and l.partner_id=%%s and l.date between %s' % (period,), (p_id,))
            res = cr.dictfetchall()
            list_partner.append(res[0]['amount'])
            list_partner.append('T') #partner.ref ...should be check
            list_partner.append(partner.vat)
            list_partner.append(country_code)
            #...deprecated...
#            addr = pool.get('res.partner').address_get(cr, uid, [partner.id], ['invoice'])
#            if addr.get('invoice',False):
#                ads = pool.get('res.partner.address').browse(cr,uid,[addr['invoice']])[0]
#
#                if ads.country_id:
#                    code_country = ads.country_id.code
#                    list_partner.append(code_country)
#                else:
#                    error_message.append('Data Insufficient! : '+ 'The Partner "'+partner.name + '"'' has no country associated with its Invoice address!')
#            if len(list_partner)<4:
#                list_partner.append('')
#                error_message.append('Data Insufficient! : '+ 'The Partner "'+partner.name + '"'' has no Invoice address!')
#            list_partner.append(code_country or 'not avail')
            record[p_id] = list_partner

        if len(error_message):
            data['form']['msg'] = 'Exception : \n' +'-'*50+'\n'+ '\n'.join(error_message)
            return data['form']
        data_clientinfo = ''

        for r in record:
            seq += 1
            amt = record[r][0] or 0
            amt = int(amt * 100)
            amount_sum += amt
            data_clientinfo +='\n\t\t<ClientList SequenceNum="'+str(seq)+'">\n\t\t\t<CompanyInfo>\n\t\t\t\t<VATNum>'+record[r][2] +'</VATNum>\n\t\t\t\t<Country>'+record[r][3] +'</Country>\n\t\t\t</CompanyInfo>\n\t\t\t<Amount>'+str(amt) +'</Amount>\n\t\t\t<Period>'+str(period_trimester) +'</Period>\n\t\t\t<Code>'+str(record[r][1]) +'</Code>\n\t\t</ClientList>'
        amount_sum = int(amount_sum)
        data_decl = '\n\t<DeclarantList SequenceNum="1" DeclarantNum="'+ dnum + '" ClientNbr="'+ str(seq) +'" AmountSum="'+ str(amount_sum) +'" >'
        data_file += str(data_decl) + str(data_comp) + str(data_period) + str(data_clientinfo) + '\n\t</DeclarantList>\n</VatIntra>'
        data['form']['msg'] = 'Save the File with '".xml"' extension.'
        data['form']['file_save'] = base64.encodestring(data_file)
        return data['form']

    states = {
        'init': {
            'actions': [_get_europe_country],
            'result': {'type': 'form', 'arch':form_intra, 'fields': fields_intra, 'state':[('end','Cancel'),('go','Create XML') ]}
                },
         'go': {
            'actions': [_create_xml],
            'result': {'type':'form', 'arch':msg_form, 'fields':msg_fields, 'state':[('end','Ok')]},
                }
             }
parter_vat_intra('vat.intra.xml')