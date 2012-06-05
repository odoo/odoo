# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2004-2012 OpenERP S.A. (<http://openerp.com>).
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
from tools.translate import _
from osv import fields, osv
from os.path import join as opj
import tools

class account_multi_charts_wizard(osv.osv_memory):
    _name = 'wizard.multi.charts.accounts'
    _inherit = 'wizard.multi.charts.accounts'
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
    
    def _load_template(self, cr, uid, template_id, company_id, code_digits=None, obj_wizard=None, account_ref={}, taxes_ref={}, tax_code_ref={}, context=None):
        res = super(account_multi_charts_wizard, self)._load_template(cr, uid, template_id, company_id, code_digits, obj_wizard, account_ref, taxes_ref, tax_code_ref, context=context)
        template = self.pool.get('account.chart.template').browse(cr, uid, template_id, context=context)
        obj_tax_temp = self.pool.get('account.tax.template')
        obj_tax = self.pool.get('account.tax')
        if obj_wizard.sales_tax == False and obj_wizard.excise_duty == False and obj_wizard.vat == False and obj_wizard.service_tax == False:
            raise osv.except_osv(_('Error !'), _('Select Tax to Install'))
        if obj_wizard.chart_template_id.name == 'India - Chart of Accounts for Public Firm':
            # Unlink the Tax for current company
            tax_ids = obj_tax.search(cr, uid, [('company_id','=',company_id)], context=context)
            obj_tax.unlink(cr, uid, tax_ids, context=context)
            #Create new Tax as per selected from wizard            
            if obj_wizard.sales_tax:
                tax_temp_ids = obj_tax_temp.search(cr, uid, [('name','in',['Sale Tax - 15%','Sale Tax - 12%']),('chart_template_id','=',obj_wizard.chart_template_id.id)], context=context)
                tax_temp_data = obj_tax_temp.browse(cr, uid, tax_temp_ids, context=context)
                taxes_ref = obj_tax_temp._generate_tax(cr, uid, tax_temp_data, tax_code_ref, company_id, context=context)
                self._tax_account(cr, uid, account_ref, taxes_ref, context=context)
            if obj_wizard.vat:
                tax_temp_ids = obj_tax_temp.search(cr, uid, [('name','in',['VAT - 5%','VAT - 15%','VAT - 8%']),('chart_template_id','=',obj_wizard.chart_template_id.id)], context=context)
                tax_temp_data = obj_tax_temp.browse(cr, uid, tax_temp_ids, context=context)
                taxes_ref = obj_tax_temp._generate_tax(cr, uid, tax_temp_data, tax_code_ref, company_id, context=context)
                self._tax_account(cr, uid, account_ref, taxes_ref, context=context)
            if obj_wizard.service_tax:
                tax_temp_ids = obj_tax_temp.search(cr, uid, [('name','in',['Service Tax','Service Tax - %2','Service Tax - %1']),('chart_template_id','=',obj_wizard.chart_template_id.id)], context=context)
                tax_temp_data = obj_tax_temp.browse(cr, uid, tax_temp_ids, context=context)
                taxes_ref = obj_tax_temp._generate_tax(cr, uid, tax_temp_data, tax_code_ref, company_id, context=context)
                self._tax_account(cr, uid, account_ref, taxes_ref, context=context)
            if obj_wizard.excise_duty:
                tax_temp_ids = obj_tax_temp.search(cr, uid, [('name','in',['Excise Duty','Excise Duty - %2','Excise Duty - 1%']),('chart_template_id','=',obj_wizard.chart_template_id.id)], context=context)
                tax_temp_data = obj_tax_temp.browse(cr, uid, tax_temp_ids, context=context)
                taxes_ref = obj_tax_temp._generate_tax(cr, uid, tax_temp_data, tax_code_ref, company_id, context=context)
                self._tax_account(cr, uid, account_ref, taxes_ref, context=context)
        elif obj_wizard.chart_template_id.name == 'India - Chart of Accounts for Partnership/Private Firm':
            # Unlink the Tax for current company
            tax_ids = obj_tax.search(cr, uid, [('company_id','=',company_id)], context=context)
            obj_tax.unlink(cr, uid, tax_ids, context=context)
            #Create new Tax as per selected from wizard            
            if obj_wizard.sales_tax:
                tax_temp_ids = obj_tax_temp.search(cr, uid, [('name','in',['Sale Tax - 15%','Sale Tax - 12%']),('chart_template_id','=',obj_wizard.chart_template_id.id)], context=context)
                tax_temp_data = obj_tax_temp.browse(cr, uid, tax_temp_ids, context=context)
                taxes_ref = obj_tax_temp._generate_tax(cr, uid, tax_temp_data, tax_code_ref, company_id, context=context)
                self._tax_account(cr, uid, account_ref, taxes_ref, context=context)
            if obj_wizard.vat:
                tax_temp_ids = obj_tax_temp.search(cr, uid, [('name','in',['VAT - 5%','VAT - 15%','VAT - 8%']),('chart_template_id','=',obj_wizard.chart_template_id.id)], context=context)
                tax_temp_data = obj_tax_temp.browse(cr, uid, tax_temp_ids, context=context)
                taxes_ref = obj_tax_temp._generate_tax(cr, uid, tax_temp_data, tax_code_ref, company_id, context=context)
                self._tax_account(cr, uid, account_ref, taxes_ref, context=context)
            if obj_wizard.service_tax:
                tax_temp_ids = obj_tax_temp.search(cr, uid, [('name','in',['Service Tax', 'Service Tax - %2', 'Service Tax - %1']),('chart_template_id','=',obj_wizard.chart_template_id.id)], context=context)
                tax_temp_data = obj_tax_temp.browse(cr, uid, tax_temp_ids, context=context)
                taxes_ref = obj_tax_temp._generate_tax(cr, uid, tax_temp_data, tax_code_ref, company_id, context=context)
                self._tax_account(cr, uid, account_ref, taxes_ref, context=context)
            if obj_wizard.excise_duty:
                tax_temp_ids = obj_tax_temp.search(cr, uid, [('name','in',['Excise Duty', 'Excise Duty - %2', 'Excise Duty - 1%']),('chart_template_id','=',obj_wizard.chart_template_id.id)], context=context)
                tax_temp_data = obj_tax_temp.browse(cr, uid, tax_temp_ids, context=context)
                taxes_ref = obj_tax_temp._generate_tax(cr, uid, tax_temp_data, tax_code_ref, company_id, context=context)
                self._tax_account(cr, uid, account_ref, taxes_ref, context=context)                                                
        return account_ref, taxes_ref, tax_code_ref
    
    def _tax_account(self, cr, uid, account_ref, taxes_ref, context=None):
        obj_tax = self.pool.get('account.tax')
        for key,value in taxes_ref['account_dict'].items():
            obj_tax.write(cr, uid, [key], { 'account_collected_id': account_ref.get(value['account_collected_id'], False),   'account_paid_id': account_ref.get(value['account_paid_id'], False),})
        return True   
     
account_multi_charts_wizard()
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
