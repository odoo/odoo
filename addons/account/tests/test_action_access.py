from odoo.tests import HttpCase, new_test_user, tagged
from odoo.tests.common import JsonRpcException


@tagged('post_install', '-at_install')
class TestActionAccess(HttpCase):

    def test_journal_entries_and_items_actions_access(self):
        new_test_user(self.env, login='invoicing_user', groups='base.group_user,account.group_account_invoice')
        new_test_user(self.env, login='readonly_user', groups='base.group_user,account.group_account_readonly')
        actions = ('account.action_move_journal_line', 'account.action_account_moves_all', 'account.action_account_moves_all_a')

        self.authenticate('invoicing_user', 'invoicing_user')
        for xml_id in actions:
            with self.subTest(xml_id=xml_id), self.assertRaises(JsonRpcException):
                self.make_jsonrpc_request('/web/action/load', {'action_id': self.env.ref(xml_id).id})
        self.assertTrue(self.make_jsonrpc_request('/web/action/load', {'action_id': 'account.action_move_out_invoice_type'}))

        self.authenticate('readonly_user', 'readonly_user')
        for xml_id in actions:
            with self.subTest(xml_id=xml_id):
                self.assertTrue(self.make_jsonrpc_request('/web/action/load', {'action_id': xml_id}))
