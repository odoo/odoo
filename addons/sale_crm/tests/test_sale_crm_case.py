# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2013-TODAY OpenERP S.A. <http://www.openerp.com>
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

from openerp.addons.mail.tests.common import TestMail

class TestSaleCrm(TestMail):

    def test_sale_crm_case(self):
        """Testing __get_bar_values method"""

        cr, uid, = self.cr, self.uid

        #Usefull models
        ir_model_obj = self.registry('ir.model.data')
        res_company_obj = self.registry('res.company')
        res_users_obj = self.registry('res.users')
        crm_case_section_obj = self.registry('crm.case.section')
        crm_lead_obj = self.registry('crm.lead')

        #Get required ids
        direct_sales_id = ir_model_obj.get_object_reference(cr, uid, 'crm', 'section_sales_department')[1]
        usd_id = ir_model_obj.get_object_reference(cr, uid, 'base', 'USD')[1]
        your_company_id = ir_model_obj.get_object_reference(cr, uid, 'base', 'main_company')[1]

        #Call _get_opportunities_data method before creating new opportunity in another currency.
        opportunities_before = crm_case_section_obj._get_opportunities_data(cr, uid, [direct_sales_id], field_name=False, arg=False, context=False)

        #Create new company with USD currency.
        res_company_id = res_company_obj.create(cr, uid,{
            'name': 'New Company',
            'currency_id': usd_id,
            'parent_id': your_company_id
          })

        #Create sales manager of new company.
        group_sale_manager_id = ir_model_obj.get_object_reference(cr, uid, 'base', 'group_sale_manager')[1]
        res_users_id = res_users_obj.create(cr, uid,{
            'name': 'User',
            'login': 'admin@example.com',
            'company_id': res_company_id,
            'company_ids': [(6, 0, [res_company_id])],
            'email': 'admin@gmail.com',
            'groups_id': [(6, 0, [group_sale_manager_id])]
          })

        #Create Opportunitie by new created user.
        opportunities_id = crm_lead_obj.create(cr, res_users_id,{
            'name': 'Opportunities',
            'type': 'opportunity',
            'planned_revenue': 10000,
            'user_id' : res_users_id,
            'section_id': direct_sales_id
          })

        user_rate = res_company_obj.browse(cr, uid, [res_company_id])[0].currency_id.rate_silent

        #Call _get_opportunities_data method and check Currency Conversion of amount for new created opportunity which was in another currency.
        opportunities_after = crm_case_section_obj._get_opportunities_data(cr, uid, [direct_sales_id], field_name=False, arg=False, context=False)
        self.assertTrue(round(opportunities_after[1]['monthly_planned_revenue'][4]['value']) == round(opportunities_before[1]['monthly_planned_revenue'][4]['value'] + (10000 / user_rate)), "Not Proper Currency Conversion for Opportunities")

        #Call _get_sale_orders_data method before changing currency of user.
        sale_order_before = crm_case_section_obj._get_sale_orders_data(cr, uid, [direct_sales_id], field_name=False, arg=False, context=False)

        #Call _get_invoices_data method before changing currency of user.
        invoice_before = crm_case_section_obj._get_invoices_data(cr, uid, [direct_sales_id], field_name=False, arg=False, context=False)

        #Change currency of company to INR.
        company_id = res_users_obj._get_company(cr, uid, context=False, uid2=False)
        inr_id = ir_model_obj.get_object_reference(cr, uid, 'base', 'INR')[1]
        res_company_obj.write(cr, uid, [company_id], {
            'currency_id': inr_id,
          })

        #Call _get_sale_orders_data method after changing currency of user.
        sale_order_after = crm_case_section_obj._get_sale_orders_data(cr, uid, [direct_sales_id], field_name=False, arg=False, context=False)

        #Call _get_invoices_data method after changing currency of user.
        invoice_after = crm_case_section_obj._get_invoices_data(cr, uid, [direct_sales_id], field_name=False, arg=False, context=False)

        new_rate = res_company_obj.browse(cr, uid, [company_id])[0].currency_id.rate_silent

        #Check currency conversion for Quotations,Sale orders and Invoices in to the current users currency
        for month in range(0,5):
            self.assertTrue(round(sale_order_before[1]['monthly_quoted'][month]['value'] * new_rate) == round(sale_order_after[1]['monthly_quoted'][month]['value']), "Currency conversion for quotations is wrong")
            self.assertTrue(round(sale_order_before[1]['monthly_confirmed'][month]['value'] * new_rate) == round(sale_order_after[1]['monthly_confirmed'][month]['value']), "Currency conversion for sale orders is wrong")
            self.assertTrue(round(invoice_before[1][month]['value'] * new_rate) == round(invoice_after[1][month]['value']), "Currency conversion for invoices is wrong")
