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

from openerp.osv import fields, osv
from openerp.tools.translate import _

class l10n_be_vat_declaration(osv.osv_memory):
    """ Vat Declaration """
    _name = "l1on_be.vat.declaration"
    _description = "Vat Declaration"

    def _get_xml_data(self, cr, uid, context=None):
        if context.get('file_save', False):
            return base64.encodestring(context['file_save'].encode('utf8'))
        return ''

    _columns = {
        'name': fields.char('File Name'),
        'period_id': fields.many2one('account.period','Period', required=True),
        'tax_code_id': fields.many2one('account.tax.code', 'Tax Code', domain=[('parent_id', '=', False)], required=True),
        'msg': fields.text('File created', readonly=True),
        'file_save': fields.binary('Save File'),
        'ask_restitution': fields.boolean('Ask Restitution',help='It indicates whether a restitution is to make or not?'),
        'ask_payment': fields.boolean('Ask Payment',help='It indicates whether a payment is to make or not?'),
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
        obj_partner = self.pool.get('res.partner')
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
            raise osv.except_osv(_('Insufficient Data!'), _('No VAT number associated with your company.'))
        vat_no = vat_no.replace(' ','').upper()
        vat = vat_no[2:]

        tax_code_ids = obj_tax_code.search(cr, uid, [('parent_id','child_of',data_tax.tax_code_id.id), ('company_id','=',obj_company.id)], context=context)
        ctx = context.copy()
        data  = self.read(cr, uid, ids)[0]
        ctx['period_id'] = data['period_id'][0]
        tax_info = obj_tax_code.read(cr, uid, tax_code_ids, ['code','sum_period'], context=ctx)

        default_address = obj_partner.address_get(cr, uid, [obj_company.partner_id.id])
        default_address_id = default_address.get("default", obj_company.partner_id.id)
        address_id= obj_partner.browse(cr, uid, default_address_id, context)

        account_period = obj_acc_period.browse(cr, uid, data['period_id'][0], context=context)
        issued_by = vat_no[:2]
        comments = data['comments'] or ''

        send_ref = str(obj_company.partner_id.id) + str(account_period.date_start[5:7]) + str(account_period.date_stop[:4])

        starting_month = account_period.date_start[5:7]
        ending_month = account_period.date_stop[5:7]
        quarter = str(((int(starting_month) - 1) / 3) + 1)

        if not address_id.email:
            raise osv.except_osv(_('Insufficient Data!'),_('No email address associated with the company.'))
        if not address_id.phone:
            raise osv.except_osv(_('Insufficient Data!'),_('No phone associated with the company.'))
        file_data = {
                        'issued_by': issued_by,
                        'vat_no': vat_no,
                        'only_vat': vat_no[2:],
                        'cmpny_name': obj_company.name,
                        'address': "%s %s"%(address_id.street or "",address_id.street2 or ""),
                        'post_code': address_id.zip or "",
                        'city': address_id.city or "",
                        'country_code': address_id.country_id and address_id.country_id.code or "",
                        'email': address_id.email or "",
                        'phone': address_id.phone.replace('.','').replace('/','').replace('(','').replace(')','').replace(' ',''),
                        'send_ref': send_ref,
                        'quarter': quarter,
                        'month': starting_month,
                        'year': str(account_period.date_stop[:4]),
                        'client_nihil': (data['client_nihil'] and 'YES' or 'NO'),
                        'ask_restitution': (data['ask_restitution'] and 'YES' or 'NO'),
                        'ask_payment': (data['ask_payment'] and 'YES' or 'NO'),
                        'comments': comments,
                     }

        data_of_file = """<?xml version="1.0"?>
<ns2:VATConsignment xmlns="http://www.minfin.fgov.be/InputCommon" xmlns:ns2="http://www.minfin.fgov.be/VATConsignment" VATDeclarationsNbr="1">
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
        cases_list = []
        for item in tax_info:
            if item['code'] == '91' and ending_month != 12:
                #the tax code 91 can only be send for the declaration of December
                continue
            if item['code'] and item['sum_period']:
                if item['code'] == 'VI':
                    if item['sum_period'] >= 0:
                        item['code'] = '71'
                    else:
                        item['code'] = '72'
                if item['code'] in list_of_tags:
                    cases_list.append(item)
        cases_list.sort()
        for item in cases_list:
            grid_amount_data = {
                    'code': str(int(item['code'])),
                    'amount': '%.2f' % abs(item['sum_period']),
                    }
            data_of_file += '\n\t\t\t<ns2:Amount GridNumber="%(code)s">%(amount)s</ns2:Amount''>' % (grid_amount_data)

        data_of_file += '\n\t\t</ns2:Data>'
        data_of_file += '\n\t\t<ns2:ClientListingNihil>%(client_nihil)s</ns2:ClientListingNihil>' % (file_data)
        data_of_file += '\n\t\t<ns2:Ask Restitution="%(ask_restitution)s" Payment="%(ask_payment)s"/>' % (file_data)
        data_of_file += '\n\t\t<ns2:Comment>%(comments)s</ns2:Comment>' % (file_data)
        data_of_file += '\n\t</ns2:VATDeclaration> \n</ns2:VATConsignment>'
        model_data_ids = mod_obj.search(cr, uid,[('model','=','ir.ui.view'),('name','=','view_vat_save')], context=context)
        resource_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
        context = dict(context or {})
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


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
