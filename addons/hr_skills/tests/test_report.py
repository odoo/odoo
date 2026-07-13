# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import HttpCase
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class SkillsTestReport(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Partner Test"})
        cls.company_A = cls.env["res.company"].create({"name": "company_A"})
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "employee_A",
                "work_contact_id": cls.partner.id,
                "company_id": cls.company_A.id,
            }
        )

    @mute_logger("odoo.http")
    def test_cv_report_traceback(self):
        template = """
        <t t-name="hr_skills.report_employee_cv">
            <t t-set="full_width" t-value="True"/>
            <t t-call="web.basic_layout">
            <div t-if ="o.no"/>
            <t t-foreach="docs" t-as="o">
                <div class="o_employee_cv page">
                    <t t-call="hr_skills.report_employee_cv_company"/>
                    <t t-call="hr_skills.report_employee_cv_sidepanel"/>
                    <t t-call="hr_skills.report_employee_cv_main_panel"/>
                    <p class="o_new_page"/>
                </div>
            </t>
            </t>
        </t>"""

        report_view = self.env.ref(
            "hr_skills.report_employee_cv", raise_if_not_found=False
        )
        self.assertTrue(report_view)
        report_view.arch = template
        wizard = self.env["hr.employee.cv.wizard"].create(
            {"employee_ids": [self.employee.id]}
        )
        view = wizard.action_validate()
        self.authenticate("admin", "admin")
        response = self.url_open(view["url"])
        self.assertRegex(response.content.decode(), "KeyError")
