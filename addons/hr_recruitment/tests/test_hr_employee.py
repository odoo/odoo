# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged, TransactionCase, Form


@tagged('-at_install', 'post_install')
class TestHrEmployee(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env['hr.employee'].create({
            'name': "Richard Stallman",
        })

    def test_job_title(self):
        first_job = self.env['hr.job'].create({'name': "first job"})
        second_job = self.env['hr.job'].create({'name': "second job"})
        with Form(self.employee) as employee_form:
            # Assign first job to employee, job title should be job name
            employee_form.job_id = first_job
            self.assertEqual(employee_form.job_title, first_job.name)

            # Change job title, job name should not change
            employee_form.job_title = "custom job title"
            self.assertEqual(first_job.name, "first job")

            # Change the name of the first job, job title should not be updated
            first_job.name = "first job modified"
            self.assertEqual(employee_form.job_title, "custom job title")
            employee_form.save()

            # Assign second job to employee, job title should be second job name
            employee_form.job_id = second_job
            self.assertEqual(employee_form.job_title, second_job.name)

            # Switch back to first job, job title should be first job name
            employee_form.job_id = first_job
            self.assertEqual(employee_form.job_title, first_job.name)
