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
from openerp.tools.translate import _
from openerp.osv import fields, osv
from openerp.report import report_sxw

class vat_listing_clients(osv.osv_memory):
    _name = 'vat.listing.clients'
    _columns = {
        'name': fields.char('Client Name', size=32),
        'vat': fields.char('VAT', size=64),
        'turnover': fields.float('Base Amount'),
        'vat_amount': fields.float('VAT Amount'),
    }

vat_listing_clients()

class partner_vat(osv.osv_memory):
    """ Vat Listing """
    _name = "partner.vat"

    def get_partner(self, cr, uid, ids, context=None):
        obj_period = self.pool.get('account.period')
        obj_partner = self.pool.get('res.partner')
        obj_vat_lclient = self.pool.get('vat.listing.clients')
        obj_model_data = self.pool.get('ir.model.data')
        obj_module = self.pool.get('ir.module.module')
        data  = self.read(cr, uid, ids)[0]
        year = data['year']
        date_start = year + '-01-01'
        date_stop = year + '-12-31'
        if context.get('company_id', False):
            company_id = context['company_id']
        else:
            company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        period_ids = obj_period.search(cr, uid, [('date_start' ,'>=', date_start), ('date_stop','<=',date_stop), ('company_id','=',company_id)])
        if not period_ids:
             raise osv.except_osv(_('Insufficient Data!'), _('No data for the selected year.'))

        partners = []
        partner_ids = obj_partner.search(cr, uid, [('vat_subjected', '!=', False), ('vat','ilike','BE%')], context=context)
        if not partner_ids:
             raise osv.except_osv(_('Error'),_('No belgium contact with a VAT number in your database.'))
        cr.execute("""SELECT sub1.partner_id, sub1.name, sub1.vat, sub1.turnover, sub2.vat_amount
                FROM (SELECT l.partner_id, p.name, p.vat, SUM(CASE WHEN c.code ='49' THEN -l.tax_amount ELSE l.tax_amount END) as turnover
                      FROM account_move_line l
                      LEFT JOIN res_partner p ON l.partner_id = p.id
                      LEFT JOIN account_tax_code c ON l.tax_code_id = c.id
                      WHERE c.code IN ('00','01','02','03','45','49')
                      AND l.partner_id IN %s
                      AND l.period_id IN %s
                      GROUP BY l.partner_id, p.name, p.vat) AS sub1
                LEFT JOIN (SELECT l2.partner_id, SUM(CASE WHEN c2.code ='64' THEN -l2.tax_amount ELSE l2.tax_amount END) as vat_amount
                      FROM account_move_line l2
                      LEFT JOIN account_tax_code c2 ON l2.tax_code_id = c2.id
                      WHERE c2.code IN ('54','64')
                      AND l2.partner_id IN %s
                      AND l2.period_id IN %s
                      GROUP BY l2.partner_id) AS sub2 ON sub1.partner_id = sub2.partner_id
                    """,(tuple(partner_ids),tuple(period_ids),tuple(partner_ids),tuple(period_ids)))
        for record in cr.dictfetchall():
            record['vat'] = record['vat'].replace(' ','').upper()
            if record['turnover'] >= data['limit_amount']:
                id_client = obj_vat_lclient.create(cr, uid, record, context=context)
                partners.append(id_client)
        
        if not partners:
            raise osv.except_osv(_('Insufficient Data!'), _('No data found for the selected year.'))
        context.update({'partner_ids': partners, 'year': data['year'], 'limit_amount': data['limit_amount']})
        model_data_ids = obj_model_data.search(cr, uid, [('model','=','ir.ui.view'), ('name','=','view_vat_listing')])
        resource_id = obj_model_data.read(cr, uid, model_data_ids, fields=['res_id'])[0]['res_id']
        return {
            'name': _('Vat Listing'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'partner.vat.list',
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

partner_vat()

class partner_vat_list(osv.osv_memory):
    """ Partner Vat Listing """
    _name = "partner.vat.list"
    _columns = {
        'partner_ids': fields.many2many('vat.listing.clients', 'vat_partner_rel', 'vat_id', 'partner_id', 'Clients', help='You can remove clients/partners which you do not want to show in xml file'),
        'name': fields.char('File Name', size=32),
        'file_save' : fields.binary('Save File', readonly=True),
        'comments': fields.text('Comments'),
    }

    def _get_partners(self, cr, uid, context=None):
        return context.get('partner_ids', [])

    _defaults={
        'partner_ids': _get_partners,
    }

    def _get_datas(self, cr, uid, ids, context=None):
        obj_vat_lclient = self.pool.get('vat.listing.clients')
        datas = []
        data = self.read(cr, uid, ids)[0]
        for partner in data['partner_ids']:
            if isinstance(partner, list) and partner:
                datas.append(partner[2])
            else:
                client_data = obj_vat_lclient.read(cr, uid, partner, context=context)
                datas.append(client_data)
        client_datas = []
        seq = 0
        sum_tax = 0.00
        sum_turnover = 0.00
        amount_data = {}
        for line in datas:
            if not line:
                continue
            seq += 1
            sum_tax += line['vat_amount']
            sum_turnover += line['turnover']
            vat = line['vat'].replace(' ','').upper()
            amount_data ={
                'seq': str(seq),
                'vat': vat,
                'only_vat': vat[2:],
                'turnover': '%.2f' %line['turnover'],
                'vat_amount': '%.2f' %line['vat_amount'],
                'sum_tax': '%.2f' %sum_tax,
                'sum_turnover': '%.2f' %sum_turnover,
                'partner_name': line['name'],
            }
            client_datas += [amount_data]
        return client_datas

    def create_xml(self, cr, uid, ids, context=None):

        obj_sequence = self.pool.get('ir.sequence')
        obj_users = self.pool.get('res.users')
        obj_partner = self.pool.get('res.partner')
        obj_model_data = self.pool.get('ir.model.data')
        seq_declarantnum = obj_sequence.get(cr, uid, 'declarantnum')
        obj_cmpny = obj_users.browse(cr, uid, uid, context=context).company_id
        company_vat = obj_cmpny.partner_id.vat

        if not company_vat:
            raise osv.except_osv(_('Insufficient Data!'),_('No VAT number associated with the company.'))

        company_vat = company_vat.replace(' ','').upper()
        SenderId = company_vat[2:]
        issued_by = company_vat[:2]
        seq_declarantnum = obj_sequence.get(cr, uid, 'declarantnum')
        dnum = company_vat[2:] + seq_declarantnum[-4:]
        street = city = country = ''
        addr = obj_partner.address_get(cr, uid, [obj_cmpny.partner_id.id], ['invoice'])
        if addr.get('invoice',False):
            ads = obj_partner.browse(cr, uid, [addr['invoice']], context=context)[0]
            phone = ads.phone and ads.phone.replace(' ','') or ''
            email = ads.email or ''
            name = ads.name or ''
            city = ads.city or ''
            zip = obj_partner.browse(cr, uid, ads.id, context=context).zip or ''
            if not city:
                city = ''
            if ads.street:
                street = ads.street
            if ads.street2:
                street += ' ' + ads.street2
            if ads.country_id:
                country = ads.country_id.code

        data = self.read(cr, uid, ids)[0]
        sender_date = time.strftime('%Y-%m-%d')
        comp_name = obj_cmpny.name

        if not email:
            raise osv.except_osv(_('Insufficient Data!'),_('No email address associated with the company.'))
        if not phone:
            raise osv.except_osv(_('Insufficient Data!'),_('No phone associated with the company.'))
        annual_listing_data = {
            'issued_by': issued_by,
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

        data_file = """<?xml version="1.0" encoding="ISO-8859-1"?>
<ns2:ClientListingConsignment xmlns="http://www.minfin.fgov.be/InputCommon" xmlns:ns2="http://www.minfin.fgov.be/ClientListingConsignment" ClientListingsNbr="1">
    <ns2:Representative>
        <RepresentativeID identificationType="NVAT" issuedBy="%(issued_by)s">%(SenderId)s</RepresentativeID>
        <Name>%(comp_name)s</Name>
        <Street>%(street)s</Street>
        <PostCode>%(zip)s</PostCode>
        <City>%(city)s</City>"""
        if annual_listing_data['country']:
            data_file +="\n\t\t<CountryCode>%(country)s</CountryCode>"
        data_file += """
        <EmailAddress>%(email)s</EmailAddress>
        <Phone>%(phone)s</Phone>
    </ns2:Representative>"""
        data_file = data_file % annual_listing_data

        data_comp = """
        <ns2:Declarant>
            <VATNumber>%(SenderId)s</VATNumber>
            <Name>%(comp_name)s</Name>
            <Street>%(street)s</Street>
            <PostCode>%(zip)s</PostCode>
            <City>%(city)s</City>
            <CountryCode>%(country)s</CountryCode>
            <EmailAddress>%(email)s</EmailAddress>
            <Phone>%(phone)s</Phone>
        </ns2:Declarant>
        <ns2:Period>%(period)s</ns2:Period>
        """ % annual_listing_data

        # Turnover and Farmer tags are not included
        client_datas = self._get_datas(cr, uid, ids, context=context)
        if not client_datas:
            raise osv.except_osv(_('Data Insufficient!'),_('No data available for the client.'))
        data_client_info = ''
        for amount_data in client_datas:
            data_client_info += """
        <ns2:Client SequenceNumber="%(seq)s">
            <ns2:CompanyVATNumber issuedBy="BE">%(only_vat)s</ns2:CompanyVATNumber>
            <ns2:TurnOver>%(turnover)s</ns2:TurnOver>
            <ns2:VATAmount>%(vat_amount)s</ns2:VATAmount>
        </ns2:Client>""" % amount_data

        amount_data_begin = client_datas[-1]
        amount_data_begin.update({'dnum':dnum})
        data_begin = """
    <ns2:ClientListing SequenceNumber="1" ClientsNbr="%(seq)s" DeclarantReference="%(dnum)s"
        TurnOverSum="%(sum_turnover)s" VATAmountSum="%(sum_tax)s">
""" % amount_data_begin

        data_end = """

        <ns2:Comment>%(comments)s</ns2:Comment>
    </ns2:ClientListing>
</ns2:ClientListingConsignment>
""" % annual_listing_data

        data_file += data_begin + data_comp + data_client_info + data_end
        file_save = base64.encodestring(data_file.encode('utf8'))
        self.write(cr, uid, ids, {'file_save':file_save, 'name':'vat_list.xml'}, context=context)
        model_data_ids = obj_model_data.search(cr, uid, [('model','=','ir.ui.view'), ('name','=','view_vat_listing_result')])
        resource_id = obj_model_data.read(cr, uid, model_data_ids, fields=['res_id'])[0]['res_id']

        return {
            'name': _('XML File has been Created'),
            'res_id': ids[0],
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'partner.vat.list',
            'views': [(resource_id,'form')],
            'context': context,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def print_vatlist(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        obj_vat_lclient = self.pool.get('vat.listing.clients')
        datas = {'ids': []}
        datas['model'] = 'res.company'
        datas['year'] = context['year']
        datas['limit_amount'] = context['limit_amount']
        datas['client_datas'] = self._get_datas(cr, uid, ids, context=context)
        if not datas['client_datas']:
            raise osv.except_osv(_('Error!'),_('No record to print.'))
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'partner.vat.listing.print',
            'datas': datas,
        }

partner_vat_list()

class partner_vat_listing_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(partner_vat_listing_print, self).__init__(cr, uid, name, context=context)
        self.localcontext.update( {
            'time': time,
        })

    def set_context(self, objects, data, ids, report_type=None):
        client_datas = data['client_datas']
        self.localcontext.update( {
            'year': data['year'],
            'sum_turnover': client_datas[-1]['sum_turnover'],
            'sum_tax': client_datas[-1]['sum_tax'],
            'client_list': client_datas,
        })
        super(partner_vat_listing_print, self).set_context(objects, data, ids)

report_sxw.report_sxw('report.partner.vat.listing.print', 'res.partner', 'addons/l10n_be/wizard/l10n_be_partner_vat_listing.rml', parser=partner_vat_listing_print,header=False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
