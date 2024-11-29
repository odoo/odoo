from odoo.addons.mail.tests.common_controllers import MailControllerThreadCommon, MessagePostSubTestData
from odoo.tests import tagged


@tagged("-at_install", "post_install", "mail_controller")
class TestProjectThreadController(MailControllerThreadCommon):
    def test_message_post_partner_ids_project(self):
        """Test partner_ids of message_post for task.
        Followers of task and followers of related project are allowed to be
        mentioned by non-internal users."""
        project = self.env["project.project"].create({"name": "Test Project"})
        task = self.env["project.task"].create({"name": "Test Task", "project_id": project.id})
        self.env["project.collaborator"].create(
            {"project_id": project.id, "partner_id": self.user_portal.partner_id.id}
        )
        token, bad_token, sign, bad_sign, partner = self._get_sign_token_params(task)
        all_partners = (
            self.user_portal + self.user_employee + self.user_employee_nopartner + self.user_admin
        ).partner_id
        project.message_subscribe(partner_ids=self.user_employee.partner_id.ids)
        task.message_subscribe(partner_ids=self.user_employee_nopartner.partner_id.ids)
        followers = (self.user_employee + self.user_employee_nopartner).partner_id

        def test_partners(user, allowed, exp_partners, route_kw=None, exp_author=None):
            return MessagePostSubTestData(
                user,
                allowed,
                partners=all_partners,
                route_kw=route_kw,
                exp_author=exp_author,
                exp_partners=exp_partners,
            )

        self._execute_message_post_subtests(
            task,
            (
                test_partners(self.user_public, False, followers),
                test_partners(self.user_public, False, followers, route_kw=bad_token),
                test_partners(self.user_public, False, followers, route_kw=bad_sign),
                test_partners(self.user_public, True, followers, route_kw=token),
                test_partners(self.user_public, True, followers, route_kw=sign, exp_author=partner),
                test_partners(self.guest, False, followers),
                test_partners(self.guest, False, followers, route_kw=bad_token),
                test_partners(self.guest, False, followers, route_kw=bad_sign),
                test_partners(self.guest, True, followers, route_kw=token),
                test_partners(self.guest, True, followers, route_kw=sign, exp_author=partner),
                test_partners(self.user_portal, True, followers),
                test_partners(self.user_portal, True, followers, route_kw=bad_token),
                test_partners(self.user_portal, True, followers, route_kw=bad_sign),
                test_partners(self.user_portal, True, followers, route_kw=token),
                test_partners(self.user_portal, True, followers, route_kw=sign),
                test_partners(self.user_employee, True, all_partners),
                test_partners(self.user_employee, True, all_partners, route_kw=bad_token),
                test_partners(self.user_employee, True, all_partners, route_kw=bad_sign),
                test_partners(self.user_employee, True, all_partners, route_kw=token),
                test_partners(self.user_employee, True, all_partners, route_kw=sign),
                test_partners(self.user_employee_nopartner, True, all_partners),
                test_partners(self.user_employee_nopartner, True, all_partners, route_kw=bad_token),
                test_partners(self.user_employee_nopartner, True, all_partners, route_kw=bad_sign),
                test_partners(self.user_employee_nopartner, True, all_partners, route_kw=token),
                test_partners(self.user_employee_nopartner, True, all_partners, route_kw=sign),
                test_partners(self.user_admin, True, all_partners),
                test_partners(self.user_admin, True, all_partners, route_kw=bad_token),
                test_partners(self.user_admin, True, all_partners, route_kw=bad_sign),
                test_partners(self.user_admin, True, all_partners, route_kw=token),
                test_partners(self.user_admin, True, all_partners, route_kw=sign),
            ),
        )
