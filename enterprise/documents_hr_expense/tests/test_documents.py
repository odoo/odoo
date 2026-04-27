# -*- coding: utf-8 -*-

import base64
from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import file_open

TEXT = base64.b64encode(bytes("workflow bridge project", 'utf-8'))


@tagged('post_install', '-at_install')
class TestCaseDocumentsBridgeExpense(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.folder_internal = cls.env.ref('documents.document_internal_folder')
        cls.folder_internal.action_update_access_rights(access_internal='edit')

        cls.documents_user = cls.env['res.users'].create({
            'name': "aaadocuments test basic user",
            'login': "aadtbu",
            'email': "aadtbu@yourcompany.com",
            'groups_id': [Command.set([cls.env.ref('documents.group_documents_user').id])],
        })

    def _create_txt_attachment_for_documents_user(self):
        with file_open('base/tests/minimal.pdf', 'rb') as f:
            pdf_file = f.read()
        return self.env['documents.document'].with_user(self.documents_user).create({
            'raw': pdf_file,
            'name': 'file.pdf',
            'mimetype': 'application/pdf',
            'folder_id': self.folder_internal.id,
        })

    def test_create_document_to_expense(self):
        """
        Makes sure the hr expense is created from the document.

        Steps:
            - Create user with employee
            - Create attachment
            - Performed action 'Create a Expense'
            - Check if the expense is created
            - Check the res_model of the document

        """
        self.documents_user.action_create_employee()  # Employee is mandatory in expense
        attachment_txt = self._create_txt_attachment_for_documents_user()

        self.assertEqual(attachment_txt.res_model, 'documents.document', "The default res model of an attachment is documents.document.")
        attachment_txt.with_user(self.documents_user).document_hr_expense_create_hr_expense()
        self.assertEqual(attachment_txt.res_model, 'hr.expense', "The attachment model is updated.")

        expense = self.env['hr.expense'].search([('id', '=', attachment_txt.res_id)])
        self.assertTrue(expense.exists(), 'expense sholud be created.')
        self.assertEqual(attachment_txt.res_id, expense.id, "Expense should be linked to attachment")

    def test_create_document_to_expense_without_employee(self):
        """
        Make sure UserError is raised when creating expense from document
        while the current user is not linked to an employee.
        """
        attachment_txt = self._create_txt_attachment_for_documents_user()
        with self.assertRaisesRegex(UserError, "You must be linked to an employee to create an expense."):
            attachment_txt.with_user(self.documents_user).document_hr_expense_create_hr_expense()

        expense = self.env['hr.expense'].search([('id', '=', attachment_txt.res_id)])
        self.assertFalse(expense.exists())
