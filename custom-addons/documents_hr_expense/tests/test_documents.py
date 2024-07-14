# -*- coding: utf-8 -*-

import base64
from odoo import Command
from odoo.tests.common import TransactionCase


TEXT = base64.b64encode(bytes("workflow bridge project", 'utf-8'))


class TestCaseDocumentsBridgeExpense(TransactionCase):

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
        folder_internal = self.env.ref('documents.documents_internal_folder')

        documents_user = self.env['res.users'].create({
            'name': "aaadocuments test basic user",
            'login': "aadtbu",
            'email': "aadtbu@yourcompany.com",
            'groups_id': [Command.set([self.env.ref('documents.group_documents_user').id])],
        })
        documents_user.action_create_employee() # Employee is mandatory in expense so i create

        attachment_txt = self.env['documents.document'].with_user(documents_user).create({
            'datas': TEXT,
            'name': 'file.txt',
            'mimetype': 'text/plain',
            'folder_id': folder_internal.id,
        })

        workflow_rule_expense = self.env['documents.workflow.rule'].create({
            'domain_folder_id': folder_internal.id,
            'name': 'workflow rule create expenses',
            'create_model': 'hr.expense',
        })

        self.assertEqual(attachment_txt.res_model, 'documents.document', "The default res model of an attachment is documents.document.")
        workflow_rule_expense.with_user(documents_user).apply_actions([attachment_txt.id])
        self.assertEqual(attachment_txt.res_model, 'hr.expense', "The attachment model is updated.")
        expense = self.env['hr.expense'].search([('id', '=', attachment_txt.res_id)])
        self.assertTrue(expense.exists(), 'expense sholud be created.')
        self.assertEqual(attachment_txt.res_id, expense.id, "Expense should be linked to attachment")
