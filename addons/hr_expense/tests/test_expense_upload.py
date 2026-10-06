# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestExpenseUpload(TransactionCase):

    def test_action_create_from_uploads(self):
        if not self.env.user.employee_id:
            self.env['hr.employee'].create({'name': 'Uploader', 'user_id': self.env.user.id})
        attachments = self.env['ir.attachment'].create([
            {'name': 'receipt1.png', 'raw': b'first'},
            {'name': 'receipt2.png', 'raw': b'second'},
        ])
        action = self.env['hr.expense'].action_create_from_uploads(attachments.ids)
        expenses = self.env['hr.expense'].search(action['domain'])
        self.assertEqual(len(expenses), 2)
        self.assertEqual(expenses.mapped('message_main_attachment_id'), attachments)
        self.assertEqual(attachments.mapped('res_model'), ['hr.expense', 'hr.expense'])
