##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
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
import time
import datetime
import pooler
import base64
from tools.translate import _

form_intra = """<?xml version="1.0"?>
<form string="Partner VAT Intra">
    <notebook>
    <page string="General Information">
    <label string="This wizard will create an XML file for Vat Intra" colspan="4"/>
    <newline/>
    <field name="period_code"/>
    <newline/>
    <field name="period_ids"/>
    <newline/>
    <field name="mand_id" help="This identifies the representative of the sending company. This is a string of 14 characters"/>
    <newline/>
    </page>
    <page string="European Countries">
    <field name="country_ids" colspan="4" nolabel="1" />
    </page>
    </notebook>
</form>"""
fields_intra = {
    'period_code': {'string':'Period Code','type':'char','size':'6','required': True, 'help': '''This is where you have to set the period code for the intracom declaration using the format: ppyyyy

  PP can stand for a month: from '01' to '12'.
  PP can stand for a trimester: '31','32','33','34'
      The first figure means that it is a trimester,
      The second figure identify the trimester.
  PP can stand for a complete fiscal year: '00'.
  YYYY stands for the year (4 positions).
'''
},
    'period_ids': {'string': 'Period(s)', 'type': 'many2many', 'relation': 'account.period', 'required': True, 'help': 'Select here the period(s) you want to include in your intracom declaration'},
    'mand_id':{'string':'MandataireId','type':'char','size':'14','required': True},
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
        company_vat = data_cmpny.partner_id.vat
        if not company_vat:
            raise wizard.except_wizard('Data Insufficient','No VAT Number Associated with Main Company!')

        seq_controlref = pool.get('ir.sequence').get(cr, uid,'controlref')
        seq_declarantnum = pool.get('ir.sequence').get(cr, uid,'declarantnum')
        cref = company_vat[2:] + seq_controlref[-4:]
        dnum = cref + seq_declarantnum[-5:]
        if len(data['form']['period_code']) != 6:
            raise wizard.except_wizard(_('Wrong Period Code'), _('The period code you entered is not valid.'))

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
        comp_name = data_cmpny.name
        data_file = '<?xml version="1.0"?>\n<VatIntra xmlns="http://www.minfin.fgov.be/VatIntra" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" RecipientId="VAT-ADMIN" SenderId="' + str(company_vat) + '"'
        data_file +=' ControlRef="' + cref + '" MandataireId="' + data['form']['mand_id'] + '" SenderDate="'+ str(sender_date)+ '"'
        data_file += ' VersionTech="1.3">'
        data_file +='\n\t<AgentRepr DecNumber="1">\n\t\t<CompanyInfo>\n\t\t\t<VATNum>' + str(company_vat)+'</VATNum>\n\t\t\t<Name>'+ comp_name +'</Name>\n\t\t\t<Street>'+ street +'</Street>\n\t\t\t<CityAndZipCode>'+  zip_city +'</CityAndZipCode>'
        data_file +='\n\t\t\t<Country>' + country +'</Country>\n\t\t</CompanyInfo>\n\t</AgentRepr>'

        data_comp ='\n\t\t<CompanyInfo>\n\t\t\t<VATNum>'+str(company_vat[2:])+'</VATNum>\n\t\t\t<Name>'+ comp_name +'</Name>\n\t\t\t<Street>'+ street +'</Street>\n\t\t\t<CityAndZipCode>'+ zip_city +'</CityAndZipCode>\n\t\t\t<Country>'+ country +'</Country>\n\t\t</CompanyInfo>'
        data_period = '\n\t\t<Period>'+ data['form']['period_code'] +'</Period>' #trimester

        error_message = []
        seq = 0
        amount_sum = 0

        list_partner = []
        data_clientinfo = ''
        cr.execute('''SELECT l.partner_id AS partner_id, p.vat AS vat, t.code AS intra_code, SUM(l.tax_amount) AS amount 
                      FROM account_move_line l 
                      LEFT JOIN account_tax_code t ON (l.tax_code_id = t.id) 
                      LEFT JOIN res_partner p ON (l.partner_id = p.id) 
                      WHERE t.code IN ('44a','44b','88') 
                       AND l.period_id IN %s 
                      GROUP BY l.partner_id, p.vat, t.code''', (tuple(data['form']['period_ids'][0][2]), ))
        for row in cr.dictfetchall():
            seq += 1
            amt = row['amount'] or 0
            amt = int(amt * 100)
            amount_sum += amt
            intra_code = row['intra_code'] == '88' and 'L' or (row['intra_code'] == '44b' and 'T' or (row['intra_code'] == '44a' and 'S' or ''))
            data_clientinfo +='\n\t\t<ClientList SequenceNum="'+str(seq)+'">\n\t\t\t<CompanyInfo>\n\t\t\t\t<VATNum>'+row['vat'][2:] +'</VATNum>\n\t\t\t\t<Country>'+row['vat'][:2] +'</Country>\n\t\t\t</CompanyInfo>\n\t\t\t<Amount>'+str(amt) +'</Amount>\n\t\t\t<Code>'+str(intra_code) +'</Code>\n\t\t</ClientList>'

        amount_sum = int(amount_sum)
        data_decl = '\n\t<DeclarantList SequenceNum="1" DeclarantNum="'+ dnum + '" ClientNbr="'+ str(seq) +'" AmountSum="'+ str(amount_sum) +'" >'
        data_file += data_decl + data_comp + str(data_period) + data_clientinfo + '\n\t</DeclarantList>\n</VatIntra>'
        data['form']['msg'] = 'Save the File with '".xml"' extension.'
        data['form']['file_save'] = base64.encodestring(data_file.encode('utf8'))
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
