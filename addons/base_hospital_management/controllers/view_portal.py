# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Cybrosys Techno Solutions (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
from odoo import http
from odoo.http import request


class ViewPortal(http.Controller):
    """Class holding portal view methods"""

    @http.route('/my/vaccinations', type='http', auth="public",
                website=True)
    def portal_my_vaccine(self, **kw):
        """Function for rendering vaccination details of portal user"""
        v_list = []
        for rec in request.env['hospital.vaccination'].sudo().search(
                [('patient_id.user_ids.id', '=', request.uid)]):
            request.env.cr.execute(
                f"""SELECT id FROM ir_attachment WHERE res_id = {rec.id} 
                    and res_model='hospital.vaccination' """)
            attachment_id = False
            attachment = request.env.cr.dictfetchall()
            if attachment:
                attachment_id = attachment[0]['id']
            data = {
                'id': rec.id,
                'name': rec.name,
                'vaccine_date': rec.vaccine_date,
                'dose': rec.dose,
                'vaccine_product_id': rec.vaccine_product_id.name,
                'vaccine_price': rec.vaccine_price,
                'attachment_id': attachment_id
            }
            v_list.append(data)
        values = {
            'vaccinations': v_list,
            'page_name': 'vaccination'
        }
        return request.render("base_hospital_management.portal_my_vaccines",
                              values)

    @http.route(['/my/tests'], type='http', auth="public", website=True)
    def portal_my_tests(self, **kw):
        """Function for rendering tests of portal user"""
        tests_list = []
        for rec in request.env['patient.lab.test'].sudo().search(
                [('patient_id.user_ids', '=', request.uid)]):
            request.env['account.move'].sudo().search(
                [('ref', '=', rec.test_id.name)
                 ], limit=1)
            data = {
                'id': rec.id,
                'name': rec.test_id.name,
                'date': rec.date
            }
            tests_list.append(data)
        values = {
            'tests': tests_list,
            'page_name': 'lab_test'
        }
        return request.render("base_hospital_management.portal_my_tests",
                              values)

    @http.route('/my/tests/<int:test_id>', type="http", auth="public",
                website=True)
    def tests_view(self, test_id):
        """Function for rendering test results of portal user"""
        result_list = []
        all_test = request.env['patient.lab.test'].sudo().browse(test_id)
        test_result_ids = request.env['lab.test.result'].sudo().search(
            [('id', 'in', all_test.result_ids.ids)])
        for rec in test_result_ids:
            query = f"""SELECT id FROM ir_attachment WHERE res_id = {rec.id} 
                                and res_model='lab.test.result' """
            request.env.cr.execute(query)
            attachment_id = False
            attachment = request.env.cr.dictfetchall()
            if attachment:
                attachment_id = attachment[0]['id']
            result_list.append({
                'id': rec.id,
                'name': rec.test_id.name,
                'result': rec.result,
                'price': rec.price,
                'attachment_id': attachment_id,
            })
        values = {
            'all_test_id': all_test.id,
            'results': result_list,
            'page_name': 'test_results'
        }
        return request.render(
            "base_hospital_management.portal_my_tests_results", values)

    @http.route('/my/op', type='http', auth="public",
                website=True)
    def portal_my_op(self, **kw):
        """Function for rendering prescriptions of portal user"""
        op = request.env['hospital.outpatient'].sudo().search_read(
            [('patient_id.user_ids.id', '=', request.uid)],
            ['op_reference', 'op_date', 'doctor_id', 'slot',
             'prescription_ids'])
        for record in op:
            hours = int(record['slot'])
            minutes = int((record['slot'] - hours) * 60)
            record['slot'] = '{:02d}:{:02d}'.format(hours, minutes)
        values = {
            'op': op,
            'page_name': 'op'
        }
        return request.render(
            "base_hospital_management.portal_my_op", values)
