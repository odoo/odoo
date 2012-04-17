# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#    
#    Adapted by Noviat to 
#     - enforce correct vat number
#     - support negative balance
#     - assign amount of tax code 71-72 correclty to grid 71 or 72
#     - support Noviat tax code scheme
#     - support multiple accounting periods per VAT declaration
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
import base64

from osv import osv, fields
from tools.translate import _

class l10n_be_vat_declaration(osv.osv_memory):
    """ Vat Declaration """
    _name = "l1on_be.vat.declaration"
    _description = "Vat Declaration"

    def _get_xml_data(self, cr, uid, context=None):
        if context.get('file_save', False):
            return base64.encodestring(context['file_save'].encode('utf8'))
        return ''

    _columns = {
        'name': fields.char('File Name', size=32),
        'period_id': fields.many2one('account.period','Period'), # kept for backward compatibility! you should use new 'period_ids' field
        'period_ids': fields.many2many('account.period', 'account_period_rel', 'acc_id', 'period_id', 'Period (s)', help = 'Select here the period(s) you want to include in your VAT declaration'),
        'tax_code_id': fields.many2one('account.tax.code', 'Tax Code', domain=[('parent_id', '=', False)], required=True),
        'msg': fields.text('File created', size=64, readonly=True),
        'file_save': fields.binary('Save File'),
        'ask_resitution': fields.boolean('Ask Restitution',help='It indicates whether a resitution is to made or not?'),
        'ask_payment': fields.boolean('Ask Payment',help='It indicates whether a payment is to made or not?'),
        'client_nihil': fields.boolean('Last Declaration, no clients in client listing', help='Tick this case only if it concerns only the last statement on the civil or cessation of activity: ' \
            'no clients to be included in the client listing.'),
        'comments': fields.text('Comments'),
    }

    def _get_tax_code(self, cr, uid, context=None):
        obj_tax_code = self.pool.get('account.tax.code')
        obj_user = self.pool.get('res.users')
        company_id = obj_user.browse(cr, uid, uid, context=context).company_id.id
        tax_code_ids = obj_tax_code.search(cr, uid, [('company_id', '=', company_id), ('parent_id', '=', False)], context=context)
        return tax_code_ids and tax_code_ids[0] or False

    _defaults = {
        'msg': 'Save the File with '".xml"' extension.',
        'file_save': _get_xml_data,
        'name': 'vat_declaration.xml',
        'tax_code_id': _get_tax_code,
    }

    def create_xml(self, cr, uid, ids, context=None):
        obj_tax_code = self.pool.get('account.tax.code')
        obj_acc_period = self.pool.get('account.period')
        obj_user = self.pool.get('res.users')
        mod_obj = self.pool.get('ir.model.data')

        if context is None:
            context = {}

        list_of_tags = ['00','01','02','03','44','45','46','47','48','49','54','55','56','57','59','61','62','63','64','71','72','81','82','83','84','85','86','87','88','91']
        data_tax = self.browse(cr, uid, ids[0])

        if not data_tax.period_id and not data_tax.period_ids:
            raise osv.except_osv(_('Data Insufficient!'),_('Please select at least one Period.'))

        if data_tax.tax_code_id:
            obj_company = data_tax.tax_code_id.company_id
        else:
            obj_company = obj_user.browse(cr, uid, uid, context=context).company_id
        vat_no = obj_company.partner_id.vat
        if not vat_no:
            raise osv.except_osv(_('Data Insufficient'), _('No VAT Number Associated with Main Company!'))
        vat_no = vat_no.replace(' ','').upper()
        vat = vat_no[2:]

        tax_code_ids = obj_tax_code.search(cr, uid, [('parent_id','child_of',data_tax.tax_code_id.id), ('company_id','=',obj_company.id)], context=context)
        ctx = context.copy()
        data  = self.read(cr, uid, ids)[0]
        tax_info = {}
        if data['period_id']:
            # using the old wizard view - convert it to period_ids
            data_period = data['period_id']
            if isinstance(data_period, (list,tuple)):
                data_period = data_period[0]
            data['period_ids'] = [ data_period ]
        for period_id in data['period_ids']:
            ctx['period_id'] = period_id #added context here
            tax_period_info = obj_tax_code.read(cr, uid, tax_code_ids, ['code','sum_period'], context=ctx)
            for c in tax_period_info:
                tax_info.update({c['code']: tax_info.get(c['code'], 0.0) + c['sum_period']})

        name = email = phone = address = post_code = city = country_code = ''
        city, post_code, address, country_code = self.pool.get('res.company')._get_default_ad(obj_company.partner_id.address)
        for addr in obj_company.partner_id.address:
            if addr.type == 'default':
                name = addr.name or ""
                email = addr.email or ""
                phone = addr.email or ""
                break

        account_periods = obj_acc_period.browse(cr, uid, data['period_ids'], context=context)
        issued_by = vat_no[:2] 
        comments = data['comments'] or ''
        
        period_end_dates = sorted([x.date_stop for x in account_periods])
        period_start_dates = sorted([x.date_start for x in account_periods])        
        send_ref = str(obj_company.partner_id.id) + period_end_dates[0][5:7] + period_end_dates[-1][:4]
        
        starting_month = period_start_dates[0][5:7]
        ending_month = period_end_dates[-1][5:7]
        quarter = str(((int(starting_month) - 1) / 3) + 1)
    
        if not country_code:
            raise osv.except_osv(_('Data Insufficient!'),_('No country associated with the company.'))
        if not email:
            raise osv.except_osv(_('Data Insufficient!'),_('No email address associated with the company.'))
        if not phone:
            raise osv.except_osv(_('Data Insufficient!'),_('No phone associated with the company.'))
        file_data = {
                        'issued_by': issued_by,
                        'vat_no': vat_no,
                        'only_vat': vat_no[2:],
                        'cmpny_name': obj_company.name,
                        'address': address,
                        'post_code': post_code,
                        'city': city,
                        'country_code': country_code,
                        'email': email,
                        'phone': phone.replace('.','').replace('/','').replace('(','').replace(')','').replace(' ',''),
                        'send_ref': send_ref,
                        'quarter': quarter,
                        'month': starting_month,
                        'year': period_end_dates[-1][:4],
                        'client_nihil': (data['client_nihil'] and 'YES' or 'NO'),
                        'ask_restitution': (data['ask_resitution'] and 'YES' or 'NO'),
                        'ask_payment': (data['ask_payment'] and 'YES' or 'NO'),
                        'comments': comments,
                     }
        
        data_of_file = """<?xml version="1.0"?>
<ns2:VATConsignment xmlns="http://www.minfin.fgov.be/InputCommon" xmlns:ns2="http://www.minfin.fgov.be/VATConsignment" VATDeclarationsNbr="1">
    <ns2:Representative>
        <RepresentativeID identificationType="NVAT" issuedBy="%(issued_by)s">%(only_vat)s</RepresentativeID>
        <Name>%(cmpny_name)s</Name>
        <Street>%(address)s</Street>
        <PostCode>%(post_code)s</PostCode>
        <City>%(city)s</City>
        <CountryCode>%(country_code)s</CountryCode>
        <EmailAddress>%(email)s</EmailAddress>
        <Phone>%(phone)s</Phone>
    </ns2:Representative>
    <ns2:VATDeclaration SequenceNumber="1" DeclarantReference="%(send_ref)s">
        <ns2:Declarant>
            <VATNumber xmlns="http://www.minfin.fgov.be/InputCommon">%(only_vat)s</VATNumber>
            <Name>%(cmpny_name)s</Name>
            <Street>%(address)s</Street>
            <PostCode>%(post_code)s</PostCode>
            <City>%(city)s</City>
            <CountryCode>%(country_code)s</CountryCode>
            <EmailAddress>%(email)s</EmailAddress>
            <Phone>%(phone)s</Phone>
        </ns2:Declarant>
        <ns2:Period>
    """ % (file_data)
         
        if starting_month != ending_month:
            #starting month and ending month of selected period are not the same
            #it means that the accounting isn't based on periods of 1 month but on quarters
            data_of_file += '\t\t<ns2:Quarter>%(quarter)s</ns2:Quarter>\n\t\t' % (file_data)
        else:
            data_of_file += '\t\t<ns2:Month>%(month)s</ns2:Month>\n\t\t' % (file_data)
        data_of_file += '\t<ns2:Year>%(year)s</ns2:Year>' % (file_data)
        data_of_file += '\n\t\t</ns2:Period>\n'
        
        data_of_file += '\t\t<ns2:Data>\t'
        
        if tax_info.get('VI') >= 0:
            tax_info['71'] = tax_info['VI']
        else:
            tax_info['72'] = tax_info.get('VI',0)
        cases_list = []
        for item in tax_info:
            if tax_info['91'] and ending_month != 12:
                #the tax code 91 can only be send for the declaration of December
                continue
            if tax_info[item] and item in list_of_tags: 
                cases_list.append(item)
        cases_list.sort()
        for item in cases_list:
            grid_amount_data = {
                    'code': str(int(item)),
                    'amount': '%.2f' %abs(tax_info[item]),
                    }
            data_of_file += '\n\t\t\t<ns2:Amount GridNumber="%(code)s">%(amount)s</ns2:Amount''>' % (grid_amount_data)
            
        data_of_file += '\n\t\t</ns2:Data>'
        data_of_file += '\n\t\t<ns2:ClientListingNihil>%(client_nihil)s</ns2:ClientListingNihil>' % (file_data)
        data_of_file += '\n\t\t<ns2:Ask Restitution="%(ask_restitution)s" Payment="%(ask_payment)s"/>' % (file_data)
        if file_data['comments']:
            data_of_file += '\n\t\t<ns2:Comment>%(comments)s</ns2:Comment>' % (file_data)
        data_of_file += '\n\t</ns2:VATDeclaration> \n</ns2:VATConsignment>'
        model_data_ids = mod_obj.search(cr, uid,[('model','=','ir.ui.view'),('name','=','view_vat_save')], context=context)
        resource_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
        context['file_save'] = data_of_file
        return {
            'name': _('Save XML For Vat declaration'),
            'context': context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'l1on_be.vat.declaration',
            'views': [(resource_id,'form')],
            'view_id': 'view_vat_save',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

l10n_be_vat_declaration()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
