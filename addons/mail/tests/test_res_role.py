# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.mail.tests.common import MailCommon, mail_new_test_user
from odoo.exceptions import UserError
from odoo.tests.common import HttpCase


class TestResRole(MailCommon, HttpCase):
    def test_role_archive_and_unlink_constraints(self):
        """ Test that archiving a role does not affect its activities, but unlinking it is prevented if in use. """
        role_activity = self.env['res.role'].create({'name': 'Activity Role'})
        role_act_type = self.env['res.role'].create({'name': 'Act Type Role'})
        role_plan = self.env['res.role'].create({'name': 'Plan Role'})
        role_action = self.env['res.role'].create({'name': 'Action Role'})
        role_free = self.env['res.role'].create({'name': 'Free Role'})
        partner_model_id = self.env['ir.model']._get_id('res.partner')
        todo_type_id = self.env.ref('mail.mail_activity_data_todo').id
        activity = self.env['mail.activity'].create({
            'activity_type_id': todo_type_id,
            'res_model_id': partner_model_id,
            'res_id': 1,
            'role_id': role_activity.id,
            'user_id': False,
        })
        self.env['mail.activity.type'].create({
            'name': 'Test Type',
            'default_role_id': role_act_type.id,
        })
        plan = self.env['mail.activity.plan'].create({
            'name': 'Test Plan',
            'res_model': 'res.partner',
        })
        self.env['mail.activity.plan.template'].create({
            'summary': 'Test Plan Activity 1',
            'plan_id': plan.id,
            'activity_type_id': todo_type_id,
            'responsible_type': 'role',
            'role_id': role_plan.id,
        })
        self.env['ir.actions.server'].create({
            'name': 'Test Action',
            'model_id': partner_model_id,
            'state': 'next_activity',
            'activity_user_type': 'role',
            'activity_role_id': role_action.id,
        })

        # --- Test Archiving ---
        role_activity.action_archive()
        self.assertFalse(role_activity.active)
        self.assertTrue(activity.exists(), "Archiving a role should not delete its activities.")
        self.assertEqual(activity.role_id, role_activity, "Archived role should remain linked to the activity.")

        # --- Test Unlink Constraints ---
        with self.assertRaisesRegex(UserError, "1 unassigned activity"):
            role_activity.unlink()
        with self.assertRaisesRegex(UserError, "Activity Types: Test Type"):
            role_act_type.unlink()
        with self.assertRaisesRegex(UserError, "Activity Plans: Test Plan Activity 1"):
            role_plan.unlink()
        with self.assertRaisesRegex(UserError, "1 Server Action"):
            role_action.unlink()

        # --- Test Successful Unlink ---
        role_free_id = role_free.id
        role_free.unlink()
        self.assertFalse(self.env['res.role'].browse(role_free_id).exists(), "Free role should be successfully deleted.")

    def test_post_mention_role(self):
        """Test mention with role"""
        contact = self.env["res.partner"].create({"name": "A contact"})
        role_discuss = self.env["res.role"].create({"name": "rd-Discuss"})
        role_js = self.env["res.role"].create({"name": "rd-JS"})
        user_discuss = mail_new_test_user(
            self.env,
            login="user_d",
            name="Discuss User",
            notification_type="inbox",
            role_ids=[Command.link(role_discuss.id)],
        )
        user_js = mail_new_test_user(
            self.env,
            login="user_js",
            name="JS User",
            notification_type="inbox",
            role_ids=[Command.link(role_js.id)],
        )
        user_discuss_js = mail_new_test_user(
            self.env,
            login="user_djs",
            name="Discuss JS User",
            notification_type="inbox",
            role_ids=[Command.link(role_discuss.id), Command.link(role_js.id)],
        )
        self.authenticate("employee", "employee")
        for [roles, expected_users] in [
            (self.env["res.role"], self.env["res.users"]),
            (role_discuss, user_discuss + user_discuss_js),
            (role_js, user_js + user_discuss_js),
            (role_discuss + role_js, user_discuss + user_js + user_discuss_js),
        ]:
            data = self.make_jsonrpc_request(
                "/mail/message/post",
                {
                    "thread_model": "res.partner",
                    "thread_id": contact.id,
                    "post_data": {
                        "body": "irrelevant",
                        "message_type": "comment",
                        "role_ids": roles.ids,
                        "subtype_xmlid": "mail.mt_note",
                    },
                },
            )
            message = next(filter(lambda m: m["id"] == data["message_id"], data["store_data"]["mail.message"]))
            self.assertEqual(
                message["partner_ids"],
                expected_users.partner_id.ids
            )
