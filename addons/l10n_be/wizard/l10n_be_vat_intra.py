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
import time
import base64
from tools.translate import _

from osv import osv, fields

class partner_vat_intra(osv.osv_memory):

    """ Partner Vat Intra"""
    _name = "partner.vat.intra"
    _description = 'Partner VAT Intra'

    def _get_europe_country(self, cursor, user, context={}):
        obj_country = self.pool.get('res.country')
        return obj_country.search(cursor, user, [('code', 'in', ['AT', 'BG', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'DE', 'GR', 'HU', 'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'NL', 'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE', 'GB'])])

    _columns = {
        'period_code': fields.char('Period Code',size = 6,required = True, help = '''This is where you have to set the period code for the intracom declaration using the format: ppyyyy
      PP can stand for a month: from '01' to '12'.
      PP can stand for a trimester: '31','32','33','34'
          The first figure means that it is a trimester,
          The second figure identify the trimester.
      PP can stand for a complete fiscal year: '00'.
      YYYY stands for the year (4 positions).
    '''
    ),
        'period_ids': fields.many2many('account.period', 'account_period_rel', 'acc_id', 'period_id', 'Period (s)', help = 'Select here the period(s) you want to include in your intracom declaration'),
        'test_xml': fields.boolean('Test XML file', help="Sets the XML output as test file"),
        'mand_id' : fields.char('MandataireId', size=14, required=True,  help="This identifies the representative of the sending company. This is a string of 14 characters"),
        'msg': fields.text('File created', size=64, readonly=True),
        'file_save' : fields.binary('Save File', readonly=True),
        'country_ids': fields.many2many('res.country', 'vat_country_rel', 'vat_id', 'country_id', 'European Countries'),
        }

    _defaults = {
        'country_ids': _get_europe_country,
                }

    def create_xml(self, cursor, user, ids, context={}):
        obj_user = self.pool.get('res.users')
        obj_fyear = self.pool.get('account.fiscalyear')
        obj_sequence = self.pool.get('ir.sequence')
        obj_partner = self.pool.get('res.partner')
        obj_partner_add = self.pool.get('res.partner.address')

        data_cmpny = obj_user.browse(cursor, user, user).company_id
        data  = self.read(cursor, user, ids)[0]
        company_vat = data_cmpny.partner_id.vat
        if not company_vat:
            raise osv.except_osv(_('Data Insufficient'),_('No VAT Number Associated with Main Company!'))

        seq_controlref = obj_sequence.get(cursor, user, 'controlref')
        seq_declarantnum = obj_sequence.get(cursor, user, 'declarantnum')
        cref = company_vat[2:] + seq_controlref[-4:]
        dnum = cref + seq_declarantnum[-5:]
        if len(data['form']['period_code']) != 6:
            raise wizard.except_wizard(_('Wrong Period Code'), _('The period code you entered is not valid.'))

        street = zip_city = country = ''
        addr = obj_partner.address_get(cursor, user, [data_cmpny.partner_id.id], ['invoice'])
        if addr.get('invoice',False):
            ads = obj_partner_add.browse(cursor, user, [addr['invoice']])[0]
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
        data_file +=' ControlRef="' + cref + '" MandataireId="' + data['mand_id'] + '" SenderDate="'+ str(sender_date)+ '"'
        data_file += ' VersionTech="1.3">'
        data_file +='\n\t<AgentRepr DecNumber="1">\n\t\t<CompanyInfo>\n\t\t\t<VATNum>' + str(company_vat)+'</VATNum>\n\t\t\t<Name>'+str(data_cmpny.name)+'</Name>\n\t\t\t<Street>'+ str(street) +'</Street>\n\t\t\t<CityAndZipCode>'+ str(zip_city) +'</CityAndZipCode>'
        data_file +='\n\t\t\t<Country>' + str(country) +'</Country>\n\t\t</CompanyInfo>\n\t</AgentRepr>'
        data_comp ='\n\t\t<CompanyInfo>\n\t\t\t<VATNum>'+str(company_vat[2:])+'</VATNum>\n\t\t\t<Name>'+str(data_cmpny.name)+'</Name>\n\t\t\t<Street>'+ str(street) +'</Street>\n\t\t\t<CityAndZipCode>'+ str(zip_city) +'</CityAndZipCode>\n\t\t\t<Country>'+ str(country) +'</Country>\n\t\t</CompanyInfo>'
        data_period = '\n\t\t<Period>'+ data['period_code'] +'</Period>' #trimester
        error_message = []
        seq = 0
        amount_sum = 0
        p_id_list = obj_partner.search(cursor, user, [('vat','!=',False)])
        if not p_id_list:
            raise osv.except_osv(_('Data Insufficient!'),_('No partner has a VAT Number asociated with him.'))

        nb_period = len(data_fiscal.period_ids)
        fiscal_periods = data_fiscal.period_ids
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
        data_file += str(data_decl) + str(data_comp) + str(data_period) + str(data_clientinfo) + '\n\t</DeclarantList>\n</VatIntra>'
        data['msg'] = 'XML Flie has been Created. Save the File with '".xml"' extension.'
        data['file_save'] = base64.encodestring(data_file)
        self.write(cursor, user, ids, {'file_save':data['file_save'], 'msg':data['msg']}, context=context)
        return True

partner_vat_intra()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
