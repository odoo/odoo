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

        # Usefull models
        ir_model_obj = self.registry('ir.model.data')
        res_company_obj = self.registry('res.company')
        res_users_obj = self.registry('res.users')
        crm_case_section_obj = self.registry('crm.case.section')
        crm_lead_obj = self.registry('crm.lead')

        # Get required ids
        direct_sales_id = ir_model_obj.get_object_reference(cr, uid, 'crm', 'section_sales_department')[1]
        usd_id = ir_model_obj.get_object_reference(cr, uid, 'base', 'USD')[1]
        your_company_id = ir_model_obj.get_object_reference(cr, uid, 'base', 'main_company')[1]

        # Call relevant methods before changing manager of sales team.
        opportunities_before = crm_case_section_obj._get_opportunities_data(cr, uid, [direct_sales_id], field_name=False, arg=False, context=False)
        sale_order_before = crm_case_section_obj._get_sale_orders_data(cr, uid, [direct_sales_id], field_name=False, arg=False, context=False)
        invoice_before = crm_case_section_obj._get_invoices_data(cr, uid, [direct_sales_id], field_name=False, arg=False, context=False)

        # Create new company with USD currency.
        res_company_id = res_company_obj.create(cr, uid,{
            'name': 'New Company',
            'currency_id': usd_id,
            'parent_id': your_company_id
          })

        # Create new user with sales manager access rights for new company.
        group_sale_manager_id = ir_model_obj.get_object_reference(cr, uid, 'base', 'group_sale_manager')[1]
        res_users_id = res_users_obj.create(cr, uid,{
            'name': 'User',
            'login': 'admin@example.com',
            'company_id': res_company_id,
            'company_ids': [(6, 0, [res_company_id])],
            'email': 'admin@gmail.com',
            'groups_id': [(6, 0, [group_sale_manager_id])]
          })

        # Change manager of sales team with USD currency.
        crm_case_section_obj.write(cr, uid, [direct_sales_id], {
            'user_id' : res_users_id,
            'currency_id': usd_id,
          })

        # Call relevant methods and get converted data in another currency.
        opportunities_after = crm_case_section_obj._get_opportunities_data(cr, uid, [direct_sales_id], field_name=False, arg=False, context=False)
        sale_order_after = crm_case_section_obj._get_sale_orders_data(cr, uid, [direct_sales_id], field_name=False, arg=False, context=False)
        invoice_after = crm_case_section_obj._get_invoices_data(cr, uid, [direct_sales_id], field_name=False, arg=False, context=False)

        team_currency_rate = crm_case_section_obj.browse(cr, uid, direct_sales_id).currency_id.rate_silent

        # Check currency conversion for Quotations,Sale orders and Invoices in to the current users currency
        for month in range(0,5):
            self.assertTrue(round(opportunities_before[1]['monthly_planned_revenue'][month]['value']) == round(opportunities_after[1]['monthly_planned_revenue'][month]['value'] / team_currency_rate), "Not Proper Currency Conversion for Opportunities")
            self.assertTrue(round(sale_order_before[1]['monthly_quoted'][month]['value']) == round(sale_order_after[1]['monthly_quoted'][month]['value'] / team_currency_rate), "Currency conversion for quotations is wrong")
            self.assertTrue(round(sale_order_before[1]['monthly_confirmed'][month]['value']) == round(sale_order_after[1]['monthly_confirmed'][month]['value'] / team_currency_rate), "Currency conversion for sale orders is wrong")
            self.assertTrue(round(invoice_before[1][month]['value']) == round(invoice_after[1][month]['value'] / team_currency_rate), "Currency conversion for invoices is wrong")
