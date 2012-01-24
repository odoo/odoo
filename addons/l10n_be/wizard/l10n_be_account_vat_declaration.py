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
        'period_id': fields.many2one('account.period','Period', required=True),
        'tax_code_id': fields.many2one('account.tax.code', 'Tax Code', domain=[('parent_id', '=', False)]),
        'msg': fields.text('File created', size=64, readonly=True),
        'file_save': fields.binary('Save File'),
        'ask_restitution': fields.boolean('Ask Restitution',help='It indicates whether a resitution is to made or not?'),
        'ask_payment': fields.boolean('Ask Payment',help='It indicates whether a payment is to made or not?'),
        'client_nihil': fields.boolean('Last Declaration of Enterprise',help='Tick this case only if it concerns only the last statement on the civil or cessation of activity'),
        'vat_declarations_nbr': fields.integer('VAT Declaration Number', help="Number of periodic VAT returns in the shipment"),
        'comments': fields.text('Comments'),
        'identification_type': fields.selection([('tin','TIN'), ('nvat','NVAT'), ('other','Other')], 'Identification Type', required=True),
        'other': fields.char('Other Qlf', size=16, help="Description of a Identification Type"),
    }
    _defaults = {
        'msg': 'Save the File with '".xml"' extension.',
        'file_save': _get_xml_data,
        'name': 'vat_declaration.xml',
        'identification_type': 'tin',
        'vat_declarations_nbr': 0,
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
        if data_tax.tax_code_id:
            obj_company = data_tax.tax_code_id.company_id
        else:
            obj_company = obj_user.browse(cr, uid, uid, context=context).company_id
        vat_no = obj_company.partner_id.vat
        if not vat_no:
            raise osv.except_osv(_('Data Insufficient'), _('No VAT Number Associated with Main Company!'))
        vat_no = vat_no.replace(' ','').upper()

        tax_code_ids = obj_tax_code.search(cr, uid, [], context=context)
        ctx = context.copy()
        data  = self.read(cr, uid, ids)[0]
        ctx['period_id'] = data['period_id'][0] #added context here
        tax_info = obj_tax_code.read(cr, uid, tax_code_ids, ['code','sum_period'], context=ctx)

        name = email = phone = address = post_code = city = country_code = ''
        name, email, phone, city, post_code, address, country_code = self.pool.get('res.company')._get_default_ad(obj_company.partner_id.address)

        account_period = obj_acc_period.browse(cr, uid, data['period_id'][0], context=context)
        issued_by = vat_no[:2] 
        comments = data['comments'] or ''
        type = data['identification_type'] or ''
        val = data['other'] or ''
            
        send_ref = str(obj_company.partner_id.id) + str(account_period.date_start[5:7]) + str(account_period.date_stop[:4])
        
        data_of_file = '<?xml version="1.0"?>\n<VATConsignment xmlns="http://www.minfin.fgov.be/VATConsignment" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" VATDeclarationsNbr="'+str(data['vat_declarations_nbr'])+'">'
        data_of_file +='\n\t<Representative> \n\t\t<RepresentativeID identificationType="'+type.upper()+'" issuedBy="'+issued_by+'" otherQlf="'+val+'">'+obj_company.company_registry+'</RepresentativeID> \n\t\t<Name>'+obj_company.name+'</Name> \n\t\t<Street>'+address+'</Street> \n\t\t<PostCode>'+post_code+'</PostCode> \n\t\t<City>'+city+'</City> \n\t\t<CountryCode>'+country_code+'</CountryCode> \n\t\t<EmailAddress>'+email+'</EmailAddress> \n\t\t<Phone>'+phone+'</Phone> \n\t</Representative>'
        data_of_file +='\n\t<RepresentativeReference></RepresentativeReference>'
        data_of_file +='\n\t<VATDeclaration SequenceNumber="1" DeclarantReference="'+send_ref+'">'
        data_of_file +='\n\t\t<ReplacedVATDeclaration></ReplacedVATDeclaration>'
        data_of_file +='\n\t\t<Declarant>\n\t\t\t<VATNUMBER xmlns="http://www.minfin.fgov.be/InputCommon">'+str(vat_no)+'</VATNUMBER>'
        data_of_file +='\n\t\t\t<Name>'+obj_company.name+'</Name>'
        data_of_file +='\n\t\t\t<Street>'+address+'</Street>'
        data_of_file +='\n\t\t\t<PostCode>'+post_code+'</PostCode>'
        data_of_file +='\n\t\t\t<City>'+city+'</City>'
        data_of_file +='\n\t\t\t<CountryCode>'+country_code+'</CountryCode>'
        data_of_file +='\n\t\t\t<EmailAddress>'+email+'</EmailAddress>'
        data_of_file +='\n\t\t\t<Phone>'+phone+'</Phone>'
        data_of_file +='\n\t\t</Declarant>'
        data_of_file +='\n\t\t<Period>\n\t\t'

        starting_month = account_period.date_start[5:7]
        ending_month = account_period.date_stop[5:7]
        if starting_month != ending_month:
            #starting month and ending month of selected period are not the same
            #it means that the accounting isn't based on periods of 1 month but on quarters
            quarter = str(((int(starting_month) - 1) / 3) + 1)
            data_of_file += '<Quarter>'+quarter+'</Quarter>\n\t\t\t'
        else:
            data_of_file += '\t<Month>'+starting_month+'</Month>\n\t\t\t'
        data_of_file += '<Year>' + str(account_period.date_stop[:4]) + '</Year>\n\t\t</Period>\n'
        data_of_file +='\t\t<Data>\t'

        cases_list = []
        for item in tax_info:
            if item['code'] == '91' and ending_month != 12:
                #the tax code 91 can only be send for the declaration of December
                continue
            if item['code']:
                if item['code'] == 'VI':
                    if item['sum_period'] >= 0:
                        item['code'] = '71'
                    else:
                        item['code'] = '72'
                if item['code'] in list_of_tags:
                    cases_list.append(item)
        cases_list.sort()
        for item in cases_list:
            data_of_file +='\n\t\t\t<Amount GridNumber="'+str(int(item['code'])) +'">' + str(abs(int(round(item['sum_period']*100)))) +  '</Amount''>'
            
        data_of_file += '\n\t\t</Data>'
        data_of_file += '\n\t\t<ClientListingNihil>'+ (data['client_nihil'] and 'YES' or 'NO') +'</ClientListingNihil>'
        data_of_file += '\n\t\t<Ask Restitution="' + (data['ask_restitution'] and 'YES' or 'NO') + '" Payment="' + (data['ask_payment'] and 'YES' or 'NO') +'"/>'
        data_of_file +='\n\t\t<FileAttachment>''</FileAttachment>'
        data_of_file +='\n\t\t<Comment>'+ comments +'</Comment>'
        data_of_file += '\n\t</VATDeclaration> \n</VATConsignment>'
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
