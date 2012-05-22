# -*- encoding: utf-8 -*-
##############################################################################
#
#    Author: Nicolas Bessi. Copyright Camptocamp SA
#    Donors: Hasa Sàrl, Open Net Sàrl and Prisme Solutions Informatique SA
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
import tools
from osv import fields, osv
from os.path import join as opj
from lxml import etree

class account_multi_charts_wizard(osv.osv_memory):
    _inherit ='wizard.multi.charts.accounts'
    _columns = {
        'sales_tax': fields.boolean('Sales tax central', help='If this field is true it allows you use Sales Tax'),     
        'vat': fields.boolean('VAT resellers',help='If this field is true it allows you use VAT'),
        'service_tax': fields.boolean('Service tax', help='If this field is true it allows you use Service tax'),
        'excise_duty': fields.boolean('Excise duty', help='If this field is true it allows you use Excise duty'),
        'is_indian_chart': fields.boolean('Flag')
    }    

    def onchange_chart_template_id(self, cr, uid, ids, chart_template_id=False, context=None):
        res = super(account_multi_charts_wizard, self).onchange_chart_template_id(cr, uid, ids, chart_template_id, context)
        tax_templ_obj = self.pool.get('account.tax.template')
        res['value'] = {'complete_tax_set': False, 'sale_tax': False, 'purchase_tax': False}        
        data = self.pool.get('account.chart.template').browse(cr, uid, chart_template_id, context=context)
        if data.name in ('Public Firm Chart of Account','Partnership/Private Firm Chart of Account'):
            res.update({'value': {'is_indian_chart': True}})
        else: 
            res.update({'value': {'is_indian_chart': False}})
        if data.complete_tax_set:
            sale_tax_ids = tax_templ_obj.search(cr, uid, [("chart_template_id"
                                          , "=", chart_template_id), ('type_tax_use', 'in', ('sale','all'))], order="sequence, id desc")
            purchase_tax_ids = tax_templ_obj.search(cr, uid, [("chart_template_id"
                                          , "=", chart_template_id), ('type_tax_use', 'in', ('purchase','all'))], order="sequence, id desc")
            res['value'].update({'sale_tax': sale_tax_ids and sale_tax_ids[0] or False, 'purchase_tax': purchase_tax_ids and purchase_tax_ids[0] or False})        
        return res
            
    def execute(self, cr, uid, ids, context=None):
        obj_multi = self.browse(cr, uid, ids[0])
        if obj_multi.chart_template_id.name == 'Public Firm Chart of Account':
            if obj_multi.sales_tax == True:
                path = tools.file_open(opj('l10n_in', 'tax', 'public_firm_sales_tax.xml'))
                tools.convert_xml_import(cr, 'l10n_in', path, {}, 'init', True, None)
                path.close()
            if obj_multi.vat == True:
                path = tools.file_open(opj('l10n_in', 'tax', 'public_firm_vat.xml'))
                tools.convert_xml_import(cr, 'l10n_in', path, {}, 'init', True, None)
                path.close()   
            if obj_multi.service_tax == True:
                path = tools.file_open(opj('l10n_in', 'tax', 'public_firm_service.xml'))
                tools.convert_xml_import(cr, 'l10n_in', path, {}, 'init', True, None)
                path.close()  
            if obj_multi.excise_duty == True:
                path = tools.file_open(opj('l10n_in', 'tax', 'public_firm_excise_duty.xml'))
                tools.convert_xml_import(cr, 'l10n_in', path, {}, 'init', True, None)
                path.close()  
        elif obj_multi.chart_template_id.name == 'Partnership/Private Firm Chart of Account':
            if obj_multi.sales_tax == True:
                path = tools.file_open(opj('l10n_in', 'tax', 'privete_sale_tax.xml'))
                tools.convert_xml_import(cr, 'l10n_in', path, {}, 'init', True, None)
                path.close() 
            if obj_multi.vat == True:
                path = tools.file_open(opj('l10n_in', 'tax', 'private_vat.xml'))
                tools.convert_xml_import(cr, 'l10n_in', path, {}, 'init', True, None)
                path.close()             
            if obj_multi.service_tax == True:
                path = tools.file_open(opj('l10n_in', 'tax', 'private_service.xml'))
                tools.convert_xml_import(cr, 'l10n_in', path, {}, 'init', True, None)
                path.close()  
            if obj_multi.excise_duty == True:
                path = tools.file_open(opj('l10n_in', 'tax', 'private_exice_duty.xml'))
                tools.convert_xml_import(cr, 'l10n_in', path, {}, 'init', True, None)
                path.close()   
        return super(account_multi_charts_wizard, self).execute(cr, uid, ids, context)

account_multi_charts_wizard()
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
