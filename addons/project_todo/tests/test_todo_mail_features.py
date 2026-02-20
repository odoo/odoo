from odoo import Command
from odoo.tests import tagged, new_test_user

from odoo.addons.mail.tests.common import MailCommon


@tagged('at_install', '-post_install')
class TestTodoMailFeatures(MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portal_user = new_test_user(
            cls.env,
            login='portal_user_test',
            groups='base.group_portal',
            name='Portal User'
        )
        cls.internal_user = new_test_user(
            cls.env,
            login='internal_user_test',
            groups='project.group_project_user',
            name='Internal User'
        )
        cls.todo = cls.env['project.task'].create({
            'name': 'Test Private To-Do',
            'project_id': False,
            'user_ids': [Command.link(cls.internal_user.id)],
        })

    def test_view_task_button_visibility(self):
        """
        Test that when a To-Do sends a notification:
        1. Internal User (who has access) receives the 'View Task' button.
        2. Portal User does NOT receive the 'View Task' button.
        """

        self.todo.message_subscribe(partner_ids=[
            self.portal_user.partner_id.id,
            self.internal_user.partner_id.id,
        ])
        with self.mock_mail_gateway():
            self.todo.message_post(
                body='Test message content',
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )

        portal_email = self._new_mails.filtered(
            lambda m: self.portal_user.partner_id in m.recipient_ids
        )
        internal_email = self._new_mails.filtered(
            lambda m: self.internal_user.partner_id in m.recipient_ids
        )

        self.assertTrue(internal_email, "Internal user should have received an email")
        self.assertIn(
            'View Task',
            internal_email.body_html,
            "The email to the internal user SHOULD contain the 'View Task' button"
        )

        self.assertTrue(portal_email, "Portal user should have received an email")
        self.assertNotIn(
            'View Task',
            portal_email.body_html,
            "The email to the portal user should NOT contain the 'View Task' button"
        )
