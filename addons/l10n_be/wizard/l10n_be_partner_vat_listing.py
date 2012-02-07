# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    Corrections & modifications by Noviat nv/sa, (http://www.noviat.be):
#    - VAT listing based upon year in stead of fiscal year
#    - sql query adapted to select only 'tax-out' move lines
#    - extra button to print readable PDF report 
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
from osv import fields, osv

class vat_listing_clients(osv.osv_memory):
    _name = 'vat.listing.clients'
    _columns = {
        'name': fields.char('Client Name', size=32),
        'vat': fields.char('VAT', size=64),
        'country': fields.char('Country', size=16),
        'amount': fields.float('Amount'),
        'turnover': fields.float('Turnover'),
    }

    def name_get(self, cr, uid, ids, context=None):
        res = self.read(cr, uid, ids, ['name', 'vat'], context=context, load='_classic_write')
        return [(r['id'], '%s - %s' % (r['name'] or '', r['vat'] or '')) for r in res]

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        args.append(['id', 'in', context['partner_ids']])
        client_ids = self.search(cr, uid, [('vat', '=', name)] + args, limit=limit, context=context)
        if not client_ids:
            client_ids = self.search(cr, uid, [('name', 'ilike', name)] + args, limit=limit, context=context)
        return self.name_get(cr, uid, client_ids, context=context)

vat_listing_clients()

class partner_vat_13(osv.osv_memory):
    """ Vat Listing """
    _name = "partner.vat_13"

    def get_partner(self, cursor, user, ids, context=None):
        obj_period = self.pool.get('account.period')
        obj_partner = self.pool.get('res.partner')
        obj_vat_lclient = self.pool.get('vat.listing.clients')
        obj_model_data = self.pool.get('ir.model.data')
        data  = self.read(cursor, user, ids)[0]
        #period = obj_period.search(cursor, user, [('fiscalyear_id', '=', data['fyear'])], context=context)
        year = data['year']
        date_start = year + '-01-01'
        date_stop = year + '-12-31'
        period = obj_period.search(cursor, user, [('date_start' ,'>=', date_start), ('date_stop','<=',date_stop)])
        if not period:
             raise osv.except_osv(_('Data Insufficient!'), _('No data for the selected Year.'))
        
        p_id_list = obj_partner.search(cursor, user, [('vat_subjected', '!=', False)], context=context)
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
            cursor.execute('select b.code, sum(credit)-sum(debit) from account_move_line l left join account_account a on (l.account_id=a.id) left join account_account_type b on (a.user_type=b.id) where b.code IN %s and l.partner_id=%s and l.period_id IN %s group by b.code',(('income','produit','tax_out'),obj_partner.id,tuple(period),))
            line_info = cursor.fetchall()
            if not line_info:
                continue

            record['vat'] = obj_partner.vat.replace(' ','').upper()

            #it seems that this listing is only for belgian customers
            record['country'] = 'BE'

            record['amount'] = 0
            record['turnover'] = 0
            record['name'] = obj_partner.name
            for item in line_info:
                if item[0] in ('income','produit'):
                    record['turnover'] += item[1]
                else:
                    record['amount'] += item[1]
            id_client = obj_vat_lclient.create(cursor, user, record, context=context)
            partners.append(id_client)
            records.append(record)
        context.update({'partner_ids': partners, 'year': data['year'], 'limit_amount': data['limit_amount']})
        model_data_ids = obj_model_data.search(cursor, user, [('model','=','ir.ui.view'), ('name','=','view_vat_listing_13')])
        resource_id = obj_model_data.read(cursor, user, model_data_ids, fields=['res_id'])[0]['res_id']
        return {
            'name': 'Vat Listing',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'partner.vat.list_13',
            'views': [(resource_id,'form')],
            'context': context,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    _columns = {
        'year': fields.char('Year', size=4, required=True),
        'limit_amount': fields.integer('Limit Amount', required=True),
    }

    _defaults={
        'year': lambda *a: str(int(time.strftime('%Y'))-1),
        'limit_amount': 250,
    }

partner_vat_13()

class partner_vat_list_13(osv.osv_memory):
    """ Partner Vat Listing """
    _name = "partner.vat.list_13"
    _columns = {
        # TODO the referenced model has been deleted at revno 4672.1.2.
        'partner_ids': fields.many2many('vat.listing.clients', 'vat_partner_rel', 'vat_id', 'partner_id', 'Clients', help='You can remove clients/partners which you do not want to show in xml file'),
        'name': fields.char('File Name', size=32),
        'msg': fields.text('File created', size=64, readonly=True),
        'file_save' : fields.binary('Save File', readonly=True),
        'identification_type': fields.selection([('tin','TIN'), ('nvat','NVAT'), ('other','Other')], 'Identification Type', required=True),
        'other': fields.char('Other Qlf', size=16, help="Description of a Identification Type"),
        'comments': fields.text('Comments'),
    }

    def _get_partners(self, cursor, user, context=None):
        return context.get('partner_ids', [])

    _defaults={
        # TODO the referenced model has been deleted at revno 4672.1.2.
        'partner_ids': _get_partners,
        'identification_type' : 'tin',
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

        company_vat = company_vat.replace(' ','').upper()
        SenderId = company_vat[2:]
        issued_by = company_vat[:2]
        cref = SenderId + seq_controlref
        dnum = cref + seq_declarantnum
        #obj_year= obj_fyear.browse(cursor, user, context['fyear'], context=context)
        street = city = country = ''
        addr = obj_partner.address_get(cursor, user, [obj_cmpny.partner_id.id], ['invoice'])
        if addr.get('invoice',False):
            ads = obj_addr.browse(cursor, user, [addr['invoice']], context=context)[0]
            phone = ads.phone or ''
            email = ads.email or ''
            name = ads.name or ''

            city = obj_addr.get_city(cursor, user, ads.id)
            zip = obj_addr.browse(cursor, user, ads.id, context=context).zip or ''
            if not city:
                city = ''
            if ads.street:
                street = ads.street + ' ' 
            if ads.street2:
                street += ads.street2
            if ads.country_id:
                country = ads.country_id.code

        data = self.read(cursor, user, ids)[0]
        other = data['other'] or ''
        sender_date = time.strftime('%Y-%m-%d')
        comp_name = obj_cmpny.name

        annual_listing_data = {
            'identificationType': data['identification_type'].upper(),
            'issued_by': issued_by,
            'other': other,
            'company_vat': company_vat,
            'comp_name': comp_name,
            'street': street,
            'zip': zip,
            'city': city,
            'country': country,
            'email': email,
            'phone': phone,
            'SenderId': SenderId,
            'period': context['year'],
            'comments': data['comments'] or ''
        }

        data_file = """<?xml version="1.0"?>
<ClientListingConsignment xmlns="http://www.minfin.fgov.be/ClientListingConsignment" ClientListingsNbr="1">
    <Representative>
        <RepresentativeID identificationType="%(identificationType)s" issuedBy="%(issued_by)s" otherQlf="%(other)s">%(company_vat)s</RepresentativeID>
        <Name>%(comp_name)s</Name>
        <Street>%(street)s</Street>
        <PostCode>%(zip)s</PostCode>
        <City>%(city)s</City>
        <CountryCode>%(country)s</CountryCode>
        <EmailAddress>%(email)s</EmailAddress>
        <Phone>%(phone)s</Phone>
    </Representative>
    <RepresentativeReference></RepresentativeReference>
""" % annual_listing_data

        data_comp = """
        <ReplacedClientListing></ReplacedClientListing> 
        <Declarant>
            <VATNumber xmlns="http://www.minfin.fgov.be/InputCommon">%(SenderId)s</VATNumber>
            <Name>%(comp_name)s</Name>
            <Street>%(street)s</Street>
            <PostCode>%(zip)s</PostCode> 
            <City>%(city)s</City> 
            <CountryCode>%(country)s</CountryCode> 
            <EmailAddress>%(email)s</EmailAddress> 
            <Phone>%(phone)s</Phone> 
        </Declarant>
        <Period>%(period)s</Period>
        """ % annual_listing_data

        error_message = []

        for partner in data['partner_ids']:
            if isinstance(partner, list) and partner:
                datas.append(partner[2])
            else:
                client_data = obj_vat_lclient.read(cursor, user, partner, context=context)
                datas.append(client_data)
        seq = 0
        data_client_info = ''
        sum_tax = 0.00
        sum_turnover = 0.00
        if len(error_message):
            return 'Exception : \n' +'-'*50+'\n'+ '\n'.join(error_message)
        amount_data = {
            'seq': str(seq),
            'dnum': dnum,
            'sum_tax': str(0),
            'sum_turnover': str(0),
        }
        for line in datas:
            vat_issued = line['vat'][:2]
            if vat_issued == 'BE':
                vat_issued = ''
            else:
                vat_issued = vat_issued
            if not line:
                continue
            if line['turnover'] < context['limit_amount']:
                continue
            seq += 1
            sum_tax += line['amount']
            sum_turnover += line['turnover']
            
            amount_data.update({
                'seq': str(seq),
                'vat_issued': vat_issued,
                'only_vat': line['vat'].replace(' ','').upper()[2:],
                'turnover': str(int(round(line['turnover'] * 100))),
                'vat_amount': str(int(round(line['amount'] * 100))),
                'sum_tax': str(int(round(sum_tax * 100))),
                'sum_turnover': str(int(round(sum_turnover * 100))),
            })
            # Turnover and Farmer tags are not included
            data_client_info += """
        <Client SequenceNumber="%(seq)s">
            <CompanyVATNumber issuedby="%(vat_issued)s">%(only_vat)s</CompanyVATNumber>
            <TurnOver>%(turnover)s</TurnOver>
            <VATAmount>%(vat_amount)s</VATAmount>
        </Client>""" % amount_data

        data_begin = """
    <ClientListing SequenceNumber="1" ClientsNbr="%(seq)s" DeclarantReference="%(dnum)s"
        TurnOverSum="%(sum_turnover)s" VATAmountSum="%(sum_tax)s">
""" % amount_data

        data_end = """
        <FileAttachment></FileAttachment>
        <Comment>%(comments)s</Comment>
    </ClientListing>
</ClientListingConsignment>
""" % annual_listing_data

        data_file += data_begin + data_comp + data_client_info + data_end
        msg = 'Save the File with '".xml"' extension.'
        file_save = base64.encodestring(data_file.encode('utf8'))
        self.write(cursor, user, ids, {'file_save':file_save, 'msg':msg, 'name':'vat_list.xml'}, context=context)
        return True

#    Not fully implemented    

#    def print_vatlist(self, cursor, user, ids, context=None):
#        if context is None:
#            context = {}
#        obj_vat_lclient = self.pool.get('vat.listing.clients')
#        client_datas = []
#        data = self.read(cursor, user, ids)[0]
#        for partner in data['partner_ids']:
#            if isinstance(partner, list) and partner:
#                client_datas.append(partner[2])
#            else:
#                client_data = obj_vat_lclient.read(cursor, user, partner, context=context)
#                client_datas.append(client_data)
#                
#        datas = {'ids': []}
#        datas['model'] = 'res.company'
#        datas['year'] = context['year']
#        datas['limit_amount'] = context['limit_amount']
#        datas['client_datas'] = client_datas
#        return {
#            'type': 'ir.actions.report.xml',
#            'report_name': 'partner.vat.listing.print',
#            'datas': datas,
#        }

partner_vat_list_13()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
