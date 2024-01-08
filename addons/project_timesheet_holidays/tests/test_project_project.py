from odoo.tests import common
from odoo.exceptions import ValidationError

class TestProjectProjectConstraints(common.TransactionCase):

    def test_company_change_with_related_time_off(self):
        # Create company A and company B
        company_A = self.env['res.company'].create({'name': 'Company A'})
        company_B = self.env['res.company'].create({'name': 'Company B'})

        # Create a project and a related time off type in company A
        project_A = self.env['project.project'].create({
            'name': 'Test Project A',
            'company_id': company_A.id})

        self.env['hr.leave.type'].create({
            'name': 'Test Time Off Type A',
            'timesheet_project_id': project_A.id,
            'company_id': company_A.id})


        # change the company of project A to company B, validation should occur
        with self.assertRaises(ValidationError, msg="You can't change the project's company because it's linked to a time off type in another company. Either match the time off type's company to the project's or leave both unset."):
            project_A.company_id = company_B.id
