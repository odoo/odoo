# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from dateutil.relativedelta import relativedelta
from unittest.mock import patch

from odoo.addons.documents.tests.test_documents_multipage import single_page_pdf
from odoo.addons.documents_hr.tests.test_documents_hr_common import TransactionCaseDocumentsHr
from odoo.addons.hr_payroll.tests.common import TestPayslipBase
from odoo.tests.common import tagged


@tagged('test_document_bridge')
class TestCaseDocumentsBridgeHR(TestPayslipBase, TransactionCaseDocumentsHr):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.payroll_manager = cls.env['res.users'].create({
            'name': "Hr payroll manager test",
            'login': "hr_payroll_manager_test",
            'email': "hr_payroll_manager_test@yourcompany.com",
            'groups_id': [(6, 0, [cls.env.ref('hr_payroll.group_hr_payroll_user').id])]
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Employee (related to doc_user_2)',
            'user_id': cls.doc_user_2.id,
            'work_contact_id': cls.doc_user_2.partner_id.id
        })
        cls.payroll_folder = cls.env['documents.document'].create({
            'name': 'Payroll',
            'type': 'folder',
            'access_internal': 'view',
        })
        cls.payroll_folder.action_update_access_rights(partners={cls.payroll_manager.partner_id: ('edit', False)})
        cls.env.user.company_id.documents_payroll_folder_id = cls.payroll_folder.id
        cls.richard_emp.user_id = cls.doc_user
        cls.contract = cls.richard_emp.contract_ids[0]
        cls.contract.state = 'open'
        cls.payslip = cls.env['hr.payslip'].create({
            'name': 'Payslip of Richard',
            'employee_id': cls.richard_emp.id,
            'contract_id': cls.contract.id,
        })

    def test_payslip_document_creation(self):
        # Set a different partner for the work_contact_id to verify that the partner of the employee user is used
        self.richard_emp.work_contact_id = self.doc_user.partner_id.copy()

        self.payslip.compute_sheet()
        self.payslip.with_context(payslip_generate_pdf=True, payslip_generate_pdf_direct=True).action_payslip_done()

        attachment = self.env['ir.attachment'].search([('res_model', '=', self.payslip._name), ('res_id', '=', self.payslip.id)])
        self.assertTrue(attachment, "Validating a payslip should have created an attachment")

        document = self.env['documents.document'].search([('attachment_id', '=', attachment.id)])
        self.assertTrue(document, "There should be a new document created from the attachment")
        self.assertEqual(document.owner_id, self.env.ref('base.user_root'), "The owner_id should be odooBot")
        self.assertEqual(document.partner_id, self.richard_emp.user_id.partner_id, "The document contact must be the user partner of the employee")
        self.assertEqual(document.folder_id, self.payroll_folder, "The document should have been created in the configured folder")
        self.assertEqual(document.access_via_link, "none")
        self.assertEqual(document.access_internal, "none")
        self.assertTrue(document.is_access_via_link_hidden)
        self.assertEqual(
            {a.partner_id: a.role for a in document.access_ids},
            {self.payroll_manager.partner_id: 'edit', self.richard_emp.user_id.partner_id: 'view'},
            "The payroll manager must have edit right on the payslip and the employee view right"
        )
        self.assertEqual(document.with_user(self.richard_emp.user_id).user_permission, 'view')
        self.assertEqual(document.with_user(self.payroll_manager.user_id).user_permission, 'edit')
        self.check_document_no_access(document, self.doc_user_2)
        self.check_document_no_access(document, self.document_manager)

    def test_hr_payslip_document_creation_permission_employee_only(self):
        """ created hr.payslip documents are only viewable by the employee and editable by payroll managers. """
        self.check_document_creation_permission(self.payslip, self.payroll_folder, self.payroll_manager)

    def test_hr_payroll_employee_declaration_document_creation_simple(self):
        """Check that the employee and the payroll folder members are given access to the declarations."""
        self._test_hr_payroll_employee_declaration_document_creation('view')

    def test_hr_payroll_employee_declaration_document_creation_employee_folder_member(self):
        """Check that the employee can be a member of the payroll folder without errors for duplicate access."""
        self.env['documents.access'].create({
            'document_id': self.payroll_folder.id,
            'partner_id': self.employee.work_contact_id.id,
            'role': 'edit',
        })
        self._test_hr_payroll_employee_declaration_document_creation('edit')

    def _test_hr_payroll_employee_declaration_document_creation(self, employee_role):
        self.assertFalse(self.payroll_folder.children_ids)
        declaration = self.env['hr.payroll.employee.declaration'].create({
            'res_model': 'hr.payslip',
            'res_id': self.payslip.id,
            'employee_id': self.employee.id,
            'pdf_file': single_page_pdf,
            'pdf_filename': 'Test Declaration.pdf',
            'state': 'pdf_to_post',
        })

        # add required hr.payroll.declaration.mixin methods
        with patch.object(
            self.env['hr.payslip'].pool['hr.payslip'],
            "_get_posted_mail_template",
            lambda s: self.env.ref('documents_hr_payroll.mail_template_new_declaration',
                                   raise_if_not_found=False),
            create=True
        ), patch.object(
            self.env['hr.payslip'].pool['hr.payslip'],
            "_get_posted_document_owner",
            lambda _s, employee: employee.user_id,
            create=True
        ):
            declaration._post_pdf()

        document = self.payroll_folder.children_ids
        self.assertEqual(document.name, 'Test Declaration.pdf')
        self.assertEqual(
            set(document.access_ids.mapped(lambda a: (a.partner_id, a.role))),
            {(self.payroll_manager.partner_id, 'edit'), (self.employee.work_contact_id, employee_role)}
        )

    def test_payslip_document_creation_with_no_partner(self):
        """Check that the payslip document is created when the employee has no partner."""
        # Ensure the employee has no partner
        self.richard_emp.user_id = False
        self.richard_emp.user_id.partner_id = False
        self.richard_emp.work_contact_id = False

        payslip = self.payslip
        payslip.compute_sheet()
        payslip.with_context(payslip_generate_pdf=True).action_payslip_done()
        self.assertTrue(payslip.queued_for_pdf, "Payslip should be queued for PDF generation when not generating directly.")

        payslip.browse()._cron_generate_pdf()

        # Check if the document is created
        document = self.env['documents.document'].search([('res_model', '=', payslip._name), ('res_id', '=', payslip.id)])
        self.assertFalse(document, "A document will not be created if the employee has no partner.")

    def test_payslip_document_unlink_delete_document(self):
        payslip_run = self.env['hr.payslip.run'].create({
            'date_start': datetime.date.today() + relativedelta(years=-1, month=8, day=1),
            'date_end': datetime.date.today() + relativedelta(years=-1, month=8, day=31),
            'name': 'Payment Test'
        })

        payslip_emp = self.env['hr.payslip.employees'].create({
            'employee_ids': [(4, self.richard_emp.id)],
        })

        payslip_emp.with_context(active_id=payslip_run.id).compute_sheet()
        payslip_run.with_context(payslip_generate_pdf=True).action_validate()

        self.env['hr.payslip']._cron_generate_pdf()

        payslip = payslip_run.slip_ids[0]

        # Check if the document are created
        documents = self.env['documents.document'].search([('res_model', '=', payslip._name), ('res_id', 'in', payslip.ids)])
        self.assertEqual(len(documents), 1)

        payslip_ids = payslip.ids

        payslip.action_payslip_draft()
        payslip_run.action_draft()
        payslip_run.unlink()

        documents = self.env['documents.document'].search([('res_model', '=', 'hr.payslip'), ('res_id', 'in', payslip_ids)])
        self.assertEqual(len(documents), 0)
