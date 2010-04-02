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
import datetime
import base64

from osv import osv, fields

class partner_vat_intra(osv.osv_memory):

    """ Partner Vat Intra"""
    _name = "partner.vat.intra"
    _description = 'Partner VAT Intra'

    def _get_europe_country(self, cursor, user, context={}):
        obj_country = self.pool.get('res.country')
        return obj_country.search(cursor, user, [('code', 'in', ['AT', 'BG', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'DE', 'GR', 'HU', 'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'NL', 'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE', 'GB'])])

    _columns = {
        'trimester': fields.selection( [('1','Jan/Feb/Mar'),
                                       ('2','Apr/May/Jun'),
                                       ('3','Jul/Aug/Sep'),
                                       ('4','Oct/Nov/Dec')],
                                        'Trimester Number', required=True, help="It will be the first digit of period"),
        'test_xml': fields.boolean('Test XML file', help="Sets the XML output as test file"),
        'mand_id' : fields.char('MandataireId', size=14, required=True,  help="This identifies the representative of the sending company. This is a string of 14 characters"),
        'fyear': fields.many2one('account.fiscalyear','Fiscal Year', required=True),
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
        data_fiscal = obj_fyear.browse(cursor, user, data['fyear'], context=context)

        company_vat = data_cmpny.partner_id.vat
        if not company_vat:
            raise osv.except_osv(_('Data Insufficient'),_('No VAT Number Associated with Main Company!'))

        seq_controlref = obj_sequence.get(cursor, user, 'controlref')
        seq_declarantnum = obj_sequence.get(cursor, user, 'declarantnum')
        cref = company_vat + seq_controlref
        dnum = cref + seq_declarantnum
        if len(data_fiscal.date_start.split('-')[0]) < 4:
            raise osv.except_osv(_('Data Insufficient'),_('Trimester year should be length of 4 digits!'))
        period_trimester = data['trimester'] + data_fiscal.date_start.split('-')[0]

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
        if data['test_xml']:
            data_file += ' Test="1"'
        data_file += ' VersionTech="1.2">'
        data_file +='\n\t<AgentRepr DecNumber="1">\n\t\t<CompanyInfo>\n\t\t\t<VATNum>' + str(company_vat)+'</VATNum>\n\t\t\t<Name>'+str(data_cmpny.name)+'</Name>\n\t\t\t<Street>'+ str(street) +'</Street>\n\t\t\t<CityAndZipCode>'+ str(zip_city) +'</CityAndZipCode>'
        data_file +='\n\t\t\t<Country>' + str(country) +'</Country>\n\t\t</CompanyInfo>\n\t</AgentRepr>'

        data_comp ='\n\t\t<CompanyInfo>\n\t\t\t<VATNum>'+str(company_vat)+'</VATNum>\n\t\t\t<Name>'+str(data_cmpny.name)+'</Name>\n\t\t\t<Street>'+ str(street) +'</Street>\n\t\t\t<CityAndZipCode>'+ str(zip_city) +'</CityAndZipCode>\n\t\t\t<Country>'+ str(country) +'</Country>\n\t\t</CompanyInfo>'
        data_period = '\n\t\t<Period>'+ str(period_trimester) +'</Period>' #trimester

        error_message = []
        seq = 0
        amount_sum = 0
        p_id_list = obj_partner.search(cursor, user, [('vat','!=',False)])
        if not p_id_list:
            raise osv.except_osv(_('Data Insufficient!'),_('No partner has a VAT Number asociated with him.'))

        nb_period = len(data_fiscal.period_ids)
        fiscal_periods = data_fiscal.period_ids

        if data['trimester'] == '1':
            if nb_period == 12:
                start_date = fiscal_periods[0].date_start
                end_date = fiscal_periods[2].date_stop
            elif nb_period == 4:
                start_date = fiscal_periods[0].date_start
                end_date = fiscal_periods[0].date_stop
        elif data['trimester'] == '2':
            if nb_period == 12:
                start_date = fiscal_periods[3].date_start
                end_date = fiscal_periods[5].date_stop
            elif nb_period == 4:
                start_date = fiscal_periods[1].date_start
                end_date = fiscal_periods[1].date_stop
        elif data['trimester'] == '3':
            if nb_period == 12:
                start_date = fiscal_periods[6].date_start
                end_date = fiscal_periods[8].date_stop
            elif nb_period == 4:
                start_date = fiscal_periods[2].date_start
                end_date = fiscal_periods[2].date_stop
        elif data['trimester'] == '4':
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
            partner = obj_partner.browse(cursor, user, p_id, context=context)
            go_ahead = False
            country_code = ''
            for ads in partner.address:
                if ads.type == 'default' and (ads.country_id and ads.country_id.id in data['country_ids']):
                    go_ahead = True
                    country_code = ads.country_id.code
                    break
            if not go_ahead:
                continue

            cursor.execute('select sum(debit)-sum(credit) as amount from account_move_line l left join account_account a on (l.account_id=a.id) where a.type in ('"'receivable'"') and l.partner_id=%%s and l.date between %s' % (period,), (p_id,))
            res = cursor.dictfetchall()
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
            data['msg'] = 'Exception : \n' +'-'*50+'\n'+ '\n'.join(error_message)
            return data['msg']
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
        data['msg'] = 'XML Flie has been Created. Save the File with '".xml"' extension.'
        data['file_save'] = base64.encodestring(data_file)
        self.write(cursor, user, ids, {'file_save':data['file_save'], 'msg':data['msg']}, context=context)
        return True

partner_vat_intra()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: