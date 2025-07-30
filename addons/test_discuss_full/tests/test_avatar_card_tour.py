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

        # hr setup for multi-company
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
                "work_phone": "123456789",
            })
        )
        cls.test_employee = test_employee
        cls.user_employee_c2.write({"employee_ids": [Command.link(test_employee.id)]})
        new_test_user(
            cls.env,
            login="base_user",
            company_ids=[Command.link(cls.env.company.id), Command.link(cls.company_2.id)],
        )

        # hr_holidays setup for multi-company
        leave_type = (
            cls.env["hr.leave.type"]
            .with_company(cls.company_2)
            .create(
                {
                    "name": "Time Off multi company",
                    "company_id": cls.company_2.id,
                    "time_type": "leave",
                    "requires_allocation": False,
                }
            )
        )
        cls.env["hr.leave"].with_company(cls.company_2).with_context(
            leave_skip_state_check=True
        ).create(
            {
                "name": "Test Leave",
                "company_id": cls.company_2.id,
                "holiday_status_id": leave_type.id,
                "employee_id": cls.test_employee.id,
                "request_date_from": (date.today() - timedelta(days=1)),
                "request_date_to": (date.today() + timedelta(days=1)),
                "state": "validate",
            }
        )

    def _setup_channel(self, user):
        self.user_employee_c2.partner_id.sudo().with_user(self.user_employee_c2).message_post(
            body="Test message in chatter",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )

    @users("admin", "hr_user")
    def test_avatar_card_tour_multi_company(self):
        self._setup_channel(self.env.user)
        self.start_tour(
            f"/odoo/res.partner/{self.user_employee_c2.partner_id.id}",
            "avatar_card_tour",
            login=self.env.user.login,
        )

    @users("base_user")
    def test_avatar_card_tour_multi_company_no_hr_access(self):
        self._setup_channel(self.env.user)
        self.start_tour(
            f"/odoo/res.partner/{self.user_employee_c2.partner_id.id}",
            "avatar_card_tour_no_hr_access",
            login=self.env.user.login,
        )
