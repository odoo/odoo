# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.documents_hr.tests.test_documents_hr_common import TransactionCaseDocumentsHr
from odoo.tests.common import tagged
from datetime import date


@tagged('post_install', '-at_install', 'test_document_bridge')
class TestCaseDocumentsBridgeHR(TransactionCaseDocumentsHr):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Employee (related to doc_user)',
            'user_id': cls.doc_user.id,
            'work_contact_id': cls.doc_user.partner_id.id
        })
        cls.leave_type = cls.env['hr.leave.type'].create({'name': 'Sick', 'requires_allocation': 'no'})
        cls.leave = cls.env['hr.leave'].create({
            'employee_id': cls.employee.id,
            'holiday_status_id': cls.leave_type.id,
            'request_date_from': date(2021, 11, 24),
            'request_date_to': date(2021, 11, 24),
        })

    def test_leave_document_creation(self):
        attachment = self.env['ir.attachment'].create({
            'datas': self.TEXT,
            'name': 'fileText_test.txt',
            'mimetype': 'text/plain',
            'res_model': self.leave._name,
            'res_id': self.leave.id,
        })

        document = self.env['documents.document'].search([('attachment_id', '=', attachment.id)])
        self.assertTrue(document.exists(), "There should be a new document created from the attachment")
        self.assertEqual(document.owner_id, self.env.ref('base.user_root'), "The owner_id should be odooBot")
        self.assertEqual(document.partner_id, self.employee.work_contact_id, "The partner_id should be the employee's address")
        self.assertEqual(document.access_via_link, "none")
        self.assertEqual(document.access_internal, "none")
        self.assertTrue(document.is_access_via_link_hidden)

    def test_hr_leave_document_creation_permission_employee_only(self):
        """ Test that created hr.leave documents are only viewable by the employee and editable by hr managers. """
        self.check_document_creation_permission(self.leave)
