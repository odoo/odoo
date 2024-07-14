# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from odoo.tests.common import tagged, new_test_user
from odoo.addons.hr_payroll.tests.common import TestPayslipBase

TEXT = base64.b64encode(bytes("documents_hr", 'utf-8'))


@tagged('test_document_bridge')
class TestCaseDocumentsBridgeHR(TestPayslipBase):

    def test_payslip_document_creation(self):
        documents_user = new_test_user(self.env, login='fgh', groups='base.group_user,documents.group_documents_user')

        folder = self.env['documents.folder'].create({'name': 'Contract folder test'})
        company = self.env.user.company_id
        company.documents_hr_settings = True
        company.documents_payroll_folder_id = folder.id
        partner = self.env['res.partner'].create({
            'name': 'Employee address',
        })
        self.richard_emp.work_contact_id = partner
        self.richard_emp.user_id = documents_user
        contract = self.richard_emp.contract_ids[0]
        contract.state = 'open'
        payslip = self.env['hr.payslip'].create({
            'name': 'Payslip of Richard',
            'employee_id': self.richard_emp.id,
            'contract_id': contract.id,
        })
        payslip.compute_sheet()
        payslip.with_context(payslip_generate_pdf=True, payslip_generate_pdf_direct=True).action_payslip_done()

        attachment = self.env['ir.attachment'].search([('res_model', '=', payslip._name), ('res_id', '=', payslip.id)])
        self.assertTrue(attachment, "Validating a payslip should have created an attachment")

        document = self.env['documents.document'].search([('attachment_id', '=', attachment.id)])
        self.assertTrue(document, "There should be a new document created from the attachment")
        self.assertEqual(document.owner_id, documents_user, "The owner_id should be the document user")
        self.assertEqual(document.partner_id, self.richard_emp.work_contact_id, "The partner_id should be the employee's address")
        self.assertEqual(document.folder_id, folder, "The document should have been created in the configured folder")
