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

from osv import fields, osv
from os.path import join as opj
import tools

class account_multi_charts_wizard(osv.osv_memory):
    _inherit ='wizard.multi.charts.accounts'
    _columns = {
        'sales_tax': fields.boolean('Sales Tax', help='If this field is true it allows you install Sales Tax'),     
        'vat': fields.boolean('VAT', help='If this field is true it allows install use VAT'),
        'service_tax': fields.boolean('Service Tax', help='If this field is true it allows you install Service tax'),
        'excise_duty': fields.boolean('Excise Duty', help='If this field is true it allows you install Excise duty'),
        'is_indian_chart': fields.boolean('Indian Chart?')
    }    

    def onchange_chart_template_id(self, cr, uid, ids, chart_template_id=False, context=None):
        res = super(account_multi_charts_wizard, self).onchange_chart_template_id(cr, uid, ids, chart_template_id, context=context)
        data = self.pool.get('account.chart.template').browse(cr, uid, chart_template_id, context=context)
        if data.name in ('India - Chart of Accounts for Public Firm', 'India - Chart of Accounts for Partnership/Private Firm'):
            res['value'].update({'is_indian_chart': True})
        else:
            res['value'].update({'is_indian_chart': False}) 
        if data.name == 'India - Chart of Accounts for Public Firm':
            res['value'].update({'sales_tax': True,'vat':True, 'service_tax':True, 'excise_duty': True})
        elif data.name == 'India - Chart of Accounts for Partnership/Private Firm':
            res['value'].update({'sales_tax': True,'vat':True})
        return res
            
    def execute(self, cr, uid, ids, context=None):
        multichart_data = self.browse(cr, uid, ids[0], context=context)
        if multichart_data.chart_template_id.name == 'India - Chart of Accounts for Public Firm':
            if multichart_data.sales_tax:
                path = tools.file_open(opj('l10n_in', 'tax', 'public_firm_sales_tax.xml'))
                tools.convert_xml_import(cr, 'l10n_in', path, {}, 'init', True, None)
                path.close()
            if multichart_data.vat:
                path = tools.file_open(opj('l10n_in', 'tax', 'public_firm_vat.xml'))
                tools.convert_xml_import(cr, 'l10n_in', path, {}, 'init', True, None)
                path.close()   
            if multichart_data.service_tax:
                path = tools.file_open(opj('l10n_in', 'tax', 'public_firm_service.xml'))
                tools.convert_xml_import(cr, 'l10n_in', path, {}, 'init', True, None)
                path.close()  
            if multichart_data.excise_duty:
                path = tools.file_open(opj('l10n_in', 'tax', 'public_firm_excise_duty.xml'))
                tools.convert_xml_import(cr, 'l10n_in', path, {}, 'init', True, None)
                path.close()  
        elif multichart_data.chart_template_id.name == 'India - Chart of Accounts for Partnership/Private Firm':
            if multichart_data.sales_tax:
                path = tools.file_open(opj('l10n_in', 'tax', 'privete_sale_tax.xml'))
                tools.convert_xml_import(cr, 'l10n_in', path, {}, 'init', True, None)
                path.close() 
            if multichart_data.vat:
                path = tools.file_open(opj('l10n_in', 'tax', 'private_vat.xml'))
                tools.convert_xml_import(cr, 'l10n_in', path, {}, 'init', True, None)
                path.close()             
            if multichart_data.service_tax:
                path = tools.file_open(opj('l10n_in', 'tax', 'private_service.xml'))
                tools.convert_xml_import(cr, 'l10n_in', path, {}, 'init', True, None)
                path.close()  
            if multichart_data.excise_duty:
                path = tools.file_open(opj('l10n_in', 'tax', 'private_exice_duty.xml'))
                tools.convert_xml_import(cr, 'l10n_in', path, {}, 'init', True, None)
                path.close()  
        res = super(account_multi_charts_wizard, self).execute(cr, uid, ids, context=context) 
        return res

account_multi_charts_wizard()
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
