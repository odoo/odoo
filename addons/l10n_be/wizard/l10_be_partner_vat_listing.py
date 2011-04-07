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
import tools
from decimal import Decimal
from osv import fields, osv

class vat_listing_clients(osv.osv_memory):
    _name = 'vat.listing.clients'
    _columns = {
        'name': fields.char('Client Name', size=64),
        'vat': fields.char('VAT', size=64),
        'country': fields.char('Country', size=64),
        'amount': fields.float('Amount'),
        'turnover': fields.float('Turnover'),
            }
    def name_get(self, cr, uid, ids, context=None):
        if not len(ids):
            return []
        return [(r['id'], r['name'] or '' + ' - ' + r['vat'] or '') \
                for r in self.read(cr, uid, ids, ['name', 'vat'],
                    context, load='_classic_write')]

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        client = self.search(cr, uid, [('vat', '=', name)]+args, limit=limit, context=context)
        if not client:
            client = self.search(cr, uid, [('name', 'ilike', '%%%s%%' % name)]+args, limit=limit, context=context)
        return self.name_get(cr, uid, client, context=context)

vat_listing_clients()

class partner_vat(osv.osv_memory):
    """ Vat Listing """
    _name = "partner.vat"

    def get_partner(self, cursor, user, ids, context=None):
        obj_period = self.pool.get('account.period')
        obj_partner = self.pool.get('res.partner')
        obj_vat_lclient = self.pool.get('vat.listing.clients')
        obj_model_data = self.pool.get('ir.model.data')
        data  = self.read(cursor, user, ids)[0]
        period = obj_period.search(cursor, user, [('fiscalyear_id', '=', data['fyear'][0])], context=context)
        p_id_list = obj_partner.search(cursor, user, [('vat_subjected', '!=', False),('customer','=',True)], context=context)
        if not p_id_list:
             raise osv.except_osv(_('Data Insufficient!'), _('No partner has a VAT Number asociated with him.'))
        partners = []
        records = []
        for obj_partner in obj_partner.browse(cursor, user, p_id_list, context=context):
            record = {} # this holds record per partner

            #This listing is only for customers located in belgium, that's the
            #reason why we skip all the partners that haven't their
            #(or one of their) default address(es) located in Belgium.
            go_ahead = False
            for ads in obj_partner.address:
                if ads.type == 'default' and (ads.country_id and ads.country_id.code == 'BE') and (obj_partner.vat or '').startswith('BE'):
                    go_ahead = True
                    break
            if not go_ahead:
                continue
            cursor.execute('select b.code, sum(credit)-sum(debit) from account_move_line l left join account_account a on (l.account_id=a.id) left join account_account_type b on (a.user_type=b.id) where b.code IN %s and l.partner_id=%s and l.period_id IN %s group by b.code',(('produit', 'tax', 'income'),obj_partner.id,tuple(period),))
            line_info = cursor.fetchall()
            if not line_info:
                continue

            record['vat'] = obj_partner.vat

            #it seems that this listing is only for belgian customers
            record['country'] = 'BE'

            record['amount'] = Decimal(str(0.0))
            record['turnover'] = Decimal(str(0.0))
            record['name'] = obj_partner.name
            for item in line_info:
                if item[0] in ('produit','income'):
                    record['turnover'] += Decimal(str(item[1]))
                else:
                    record['amount'] += Decimal(str(item[1]))
            id_client = obj_vat_lclient.create(cursor, user, record, context=context)
            partners.append(id_client)
            records.append(record)
        context.update({'partner_ids': partners, 'fyear': data['fyear'], 'limit_amount': data['limit_amount'], 'mand_id':data['mand_id']})
        model_data_ids = obj_model_data.search(cursor, user, [('model','=','ir.ui.view'), ('name','=','view_vat_listing')])
        resource_id = obj_model_data.read(cursor, user, model_data_ids, fields=['res_id'])[0]['res_id']
        return {
            'name': 'Vat Listing',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'partner.vat.list',
            'views': [(resource_id,'form')],
            'context': context,
            'type': 'ir.actions.act_window',
            'target': 'new',
            }

    _columns = {
        'fyear': fields.many2one('account.fiscalyear','Fiscal Year', required=True),
        'mand_id': fields.char('MandataireId', size=14, required=True,  help="This identifies the representative of the sending company. This is a string of 14 characters"),
        'limit_amount': fields.integer('Limit Amount', required=True),
        'test_xml': fields.boolean('Test XML file', help="Sets the XML output as test file"),
        }
partner_vat()

class partner_vat_list(osv.osv_memory):

    """ Partner Vat Listing """
    _name = "partner.vat.list"
    _columns = {
        'partner_ids': fields.many2many('vat.listing.clients', 'vat_partner_rel', 'vat_id', 'partner_id', 'Clients', required=False, help='You can remove clients/partners which you do not want to show in xml file'),
        'name': fields.char('File Name', size=32),
        'msg': fields.text('File created', size=64, readonly=True),
        'file_save' : fields.binary('Save File', readonly=True),
        }

    def _get_partners(self, cursor, user, context=None):
        return context.get('partner_ids', [])

    _defaults={
        'partner_ids': _get_partners
            }

    def create_xml(self, cursor, user, ids, context=None):
        datas = []
        obj_sequence = self.pool.get('ir.sequence')
        obj_users = self.pool.get('res.users')
        obj_partner = self.pool.get('res.partner')
        obj_fyear = self.pool.get('account.fiscalyear')
        obj_addr = self.pool.get('res.partner.address')
        obj_vat_lclient = self.pool.get('vat.listing.clients')

        seq_controlref = obj_sequence.get(cursor, user, 'controlref')
        seq_declarantnum = obj_sequence.get(cursor, user, 'declarantnum')
        obj_cmpny = obj_users.browse(cursor, user, user, context=context).company_id
        company_vat = obj_cmpny.partner_id.vat
        if not company_vat:
            raise osv.except_osv(_('Data Insufficient'),_('No VAT Number Associated with Main Company!'))

        cref = company_vat + seq_controlref
        dnum = cref[2:] + (seq_declarantnum or '')
        obj_year= obj_fyear.browse(cursor, user, context['fyear'][0], context=context)
        street = zip_city = country = ''
        addr = obj_partner.address_get(cursor, user, [obj_cmpny.partner_id.id], ['invoice'])
        if addr.get('invoice',False):
            ads = obj_addr.browse(cursor, user, [addr['invoice']], context=context)[0]

            zip_city = obj_addr.get_city(cursor, user, ads.id)
            if not zip_city:
                zip_city = ''
            if ads.street:
                street = ads.street
            if ads.street2:
                street += ads.street2
            if ads.country_id:
                country = ads.country_id.code

        sender_date = time.strftime('%Y-%m-%d')
#        comp_name = obj_cmpny.name
        data_file = '<?xml version="1.0"?>\n<VatList xmlns="http://www.minfin.fgov.be/VatList" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.minfin.fgov.be/VatList VatList.xml" RecipientId="VAT-ADMIN" SenderId="'+ str(company_vat) + '"'
        data_file +=' ControlRef="'+ cref[2:] + '" MandataireId="'+ tools.ustr(context['mand_id']) + '" SenderDate="'+ str(sender_date)+ '"'
        if ['test_xml']:
            data_file += ' Test="0"'
        data_file += ' VersionTech="1.3">'
        data_file += '\n<AgentRepr DecNumber="1">\n\t<CompanyInfo>\n\t\t<VATNum>'+str(company_vat)+'</VATNum>\n\t\t<Name>'+ tools.ustr(obj_cmpny.name) +'</Name>\n\t\t<Street>'+ tools.ustr(street) +'</Street>\n\t\t<CityAndZipCode>'+ tools.ustr(zip_city) +'</CityAndZipCode>'
        data_file += '\n\t\t<Country>'+ tools.ustr(country) +'</Country>\n\t</CompanyInfo>\n</AgentRepr>'
        data_comp = '\n<CompanyInfo>\n\t<VATNum>'+str(company_vat)+'</VATNum>\n\t<Name>'+ tools.ustr(obj_cmpny.name) +'</Name>\n\t<Street>'+ tools.ustr(street) +'</Street>\n\t<CityAndZipCode>'+ tools.ustr(zip_city) +'</CityAndZipCode>\n\t<Country>'+ tools.ustr(country) +'</Country>\n</CompanyInfo>'
        data_period = '\n<Period>'+ tools.ustr(obj_year.date_stop[:4]) +'</Period>'
        error_message = []
        data = self.read(cursor, user, ids)[0]
        for partner in data['partner_ids']:
            if isinstance(partner, list) and partner:
                datas.append(partner[2])
            else:
                client_data = obj_vat_lclient.read(cursor, user, partner, context=context)
                datas.append(client_data)
        seq = 0
        data_clientinfo = ''
        sum_tax = Decimal(str(0.00))
        sum_turnover=Decimal(str(0.00))
        if len(error_message):
            return 'Exception : \n' +'-'*50+'\n'+ '\n'.join(error_message)
        for line in datas:
            if not line:
                continue
            if Decimal(str(line['turnover'])) < Decimal(str(context['limit_amount'])):
                continue
            seq += 1
            sum_tax +=Decimal(str(line['amount']))
            sum_turnover +=Decimal(str(line['turnover']))
            data_clientinfo += '\n<ClientList SequenceNum="'+str(seq)+'">\n\t<CompanyInfo>\n\t\t<VATNum>'+ (line['vat'] or '')[2:] +'</VATNum>\n\t\t<Country>' + tools.ustr(line['country']) +'</Country>\n\t</CompanyInfo>\n\t<Amount>'+ str(int(Decimal(str(line['amount'] * 100)))) +'</Amount>\n\t<TurnOver>'+ str(int(Decimal(str(line['turnover'] * 100)))) +'</TurnOver>\n</ClientList>'

        data_decl ='\n<DeclarantList SequenceNum="1" DeclarantNum="'+ dnum + '" ClientNbr="'+ str(seq) +'" TurnOverSum="'+ str(int(Decimal(str(sum_turnover * 100)))) +'" TaxSum="'+ str(int(Decimal(str(sum_tax * 100)))) +'">'
        data_file += tools.ustr(data_decl) + tools.ustr(data_comp) + tools.ustr(data_period) + tools.ustr(data_clientinfo) + '\n</DeclarantList></VatList>'
        msg = 'Save the File with '".xml"' extension.'
        file_save = base64.encodestring(data_file.encode('utf8'))
        self.write(cursor, user, ids, {'file_save':file_save, 'msg':msg, 'name':'vat_list.xml'}, context=context)
        return True

partner_vat_list()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
