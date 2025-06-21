from datetime import date, timedelta

from odoo import Command
from odoo.tests import tagged, users
from odoo.tests.common import HttpCase, new_test_user
from odoo.addons.mail.tests.common import MailCommon


@tagged("post_install", "-at_install")
class TestAvatarCardTour(MailCommon, HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        new_test_user(
            cls.env,
            login="hr_user",
            company_ids=[Command.link(cls.env.company.id), Command.link(cls.company_2.id)],
            groups="hr.group_hr_user",
        )
        leave_type = (
            cls.env["hr.leave.type"]
            .with_company(cls.company_2)
            .create({
                "name": "Time Off multi company",
                "company_id": cls.company_2.id,
                "time_type": "leave",
                "requires_allocation": False,
            })
        )
        department = (
            cls.env["hr.department"]
            .with_company(cls.company_2)
            .create({"name": "Test Department", "company_id": cls.company_2.id})
        )
        job = (
            cls.env["hr.job"]
            .with_company(cls.company_2)
            .create({"name": "Test Job Title", "company_id": cls.company_2.id})
        )
        other_partner = (
            cls.env["res.partner"]
            .with_company(cls.company_2)
            .create({
                "name": "Test Other Partner",
                "company_id": cls.company_2.id,
                "phone": "987654321",
            })
        )
        test_employee = (
            cls.env["hr.employee"]
            .with_company(cls.company_2)
            .create({
                "name": "Test Employee",
                "user_id": cls.user_employee_c2.id,
                "company_id": cls.company_2.id,
                "department_id": department.id,
                "job_id": job.id,
                "address_id": other_partner.id,
                "work_email": "test_employee@test.com",
            })
        )
        cls.user_employee_c2.write({"employee_ids": [Command.link(test_employee.id)]})
        cls.env["hr.leave"].with_company(cls.company_2).with_context(
            leave_skip_state_check=True
        ).create({
            "name": "Test Leave",
            "company_id": cls.company_2.id,
            "holiday_status_id": leave_type.id,
            "employee_id": test_employee.id,
            "request_date_from": (date.today() - timedelta(days=1)),
            "request_date_to": (date.today() + timedelta(days=1)),
            "state": "validate",
        })

    def _setup_channel(self, user):
        channel = (
            self.env["discuss.channel"]
            .sudo()
            .create({
                "name": "Test Chat",
                "channel_type": "chat",
                "channel_member_ids": [
                    Command.create({"partner_id": self.user_employee_c2.partner_id.id}),
                    Command.create({"partner_id": user.partner_id.id}),
                ],
            })
        )
        channel.with_user(self.user_employee_c2).message_post(
            body="Test message in chat",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )

    @users("admin", "hr_user")
    def test_avatar_card_tour_multi_company(self):
        self._setup_channel(self.env.user)
        self.start_tour("/", "avatar_card_tour", login=self.env.user.login)

    def test_avatar_card_tour_no_access(self):
        user_no_access = new_test_user(
            self.env,
            login="user_no_access",
            company_ids=[Command.link(self.env.company.id), Command.link(self.company_2.id)],
        )
        self.uid = user_no_access.id
        self._setup_channel(user_no_access)
        self.start_tour("/", "avatar_card_tour_no_access", login=user_no_access.login)
