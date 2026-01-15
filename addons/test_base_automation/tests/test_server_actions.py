# # Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.base.models.ir_actions import ServerActionWithWarningsError
from odoo.exceptions import ValidationError
from odoo.addons.base.tests.test_ir_actions import TestServerActionsBase


class TestServerActionsValidation(TestServerActionsBase):
    def test_multi_action_children_warnings(self):
        self.action.write({
            'state': 'multi',
            'child_ids': [self.test_server_action.id]
        })
        self.assertEqual(self.action.model_id.model, "res.partner")
        self.assertEqual(self.test_server_action.model_id.model, "ir.actions.server")
        self.assertEqual(self.action.warning, "Following child actions should have the same model (Contact): TestDummyServerAction")

        new_action = self.action.copy()
        with self.assertRaises(ValidationError) as ve:
            new_action.write({
                'child_ids': [self.action.id]
            })
        self.assertEqual(ve.exception.args[0], "Following child actions have warnings: TestAction")

    def test_webhook_payload_includes_group_restricted_fields(self):
        self.test_server_action.write({
            'state': 'webhook',
            'webhook_field_ids': [self.env['ir.model.fields']._get('ir.actions.server', 'code').id],
        })
        self.assertEqual(self.test_server_action.warning, "Group-restricted fields cannot be included in "
            "webhook payloads, as it could allow any user to "
            "accidentally leak sensitive information. You will "
            "have to remove the following fields from the webhook payload:\n"
            "- Python Code")

    def test_recursion_in_child(self):
        new_action = self.action.copy()
        self.action.write({
            'state': 'multi',
            'child_ids': [new_action.id]
        })
        with self.assertRaises(ValidationError) as ve:
            new_action.write({
                'child_ids': [self.action.id]
            })
        self.assertEqual(ve.exception.args[0], "Recursion found in child server actions")

    def test_non_relational_field_traversal(self):
        self.action.write({
            'state': 'object_write',
            'update_path': 'parent_id.name',
            'value': 'TestNew',
        })
        with self.assertRaises(ValidationError) as ve:
            self.action.write({'update_path': 'parent_id.name.something_else'})
        self.assertEqual(ve.exception.args[0], "The path contained by the field "
                        "'Field to Update Path' contains a non-relational field"
                        " (Name) that is not the last field in the path. You "
                        "can't traverse non-relational fields (even in the quantum"
                        " realm). Make sure only the last field in the path is non-relational.")

    def test_python_bad_expr(self):
        with self.assertRaises(ValidationError) as ve:
            self.test_server_action.write({'code': 'this is invalid python code'})
        self.assertEqual(
            ve.exception.args[0],
            "SyntaxError : invalid syntax at line 1\n"
            "this is invalid python code\n")

    def test_cannot_run_if_warnings(self):
        self.action.write({
            'state': 'multi',
            'child_ids': [self.test_server_action.id]
        })
        self.assertTrue(self.action.warning)
        with self.assertRaises(ServerActionWithWarningsError) as e:
            self.action.run()
        self.assertEqual(e.exception.args[0], "Server action TestAction has one or more warnings, address them first.")
