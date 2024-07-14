# -*- coding: utf-8 -*-
import base64

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestInvoices(AccountTestInvoicingCommon):

    def test_suspense_statement_line_id(self):
        reconcile_activity_type = self.env['mail.activity.type'].create({
            "name": "Reconciliation request",
            "category": "upload_file",
            "folder_id": self.env.ref("documents.documents_finance_folder").id,
            "res_model": "account.move",
            "tag_ids": [(6, 0, [self.env.ref('documents.documents_finance_status_tc').id])],
        })

        st = self.env['account.bank.statement'].create({
            'line_ids': [Command.create({
                'amount': -1000.0,
                'date': '2017-01-01',
                'journal_id': self.company_data['default_journal_bank'].id,
                'payment_ref': 'test_suspense_statement_line_id',
            })],
        })
        st.balance_end_real = st.balance_end
        st_line = st.line_ids
        move = st_line.move_id

        # Log an activity on the move using the "Reconciliation Request".
        activity = self.env['mail.activity'].create({
            'activity_type_id': reconcile_activity_type.id,
            'note': "test_suspense_statement_line_id",
            'res_id': move.id,
            'res_model_id': self.env.ref('account.model_account_move').id,
        })
        activity._onchange_activity_type_id()

        # A new document has been created.
        documents = self.env['documents.document'].search([('request_activity_id', '=', activity.id)])
        self.assertTrue(documents.exists())

        # Upload an attachment.
        attachment = self.env['ir.attachment'].create({
            'name': "test_suspense_statement_line_id",
            'datas': base64.b64encode(bytes("test_suspense_statement_line_id", 'utf-8')),
            'res_model': move._name,
            'res_id': move.id,
        })
        activity._action_done(attachment_ids=attachment.ids)

        # Upload as a vendor bill.
        workflow_rule_vendor_bill = self.env['documents.workflow.rule'].create({
            'domain_folder_id': documents.folder_id.id,
            'name': "Create a new Vendor Bill from document",
            'create_model': 'account.move.in_invoice',
        })
        vendor_bill_action = workflow_rule_vendor_bill.apply_actions(documents.ids)
        self.assertTrue(vendor_bill_action.get('res_id'))
        vendor_bill = self.env['account.move'].browse(vendor_bill_action['res_id'])

        self.assertRecordValues(vendor_bill, [{'suspense_statement_line_id': st_line.id}])
