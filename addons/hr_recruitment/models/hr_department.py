from odoo import fields, models


class HrDepartment(models.Model):
    _inherit = "hr.department"

    new_applicant_count = fields.Integer(
        compute="_compute_new_applicant_count",
        string="New Applicant",
        compute_sudo=True,
    )
    new_hired_employee = fields.Integer(compute="_compute_recruitment_stats")
    expected_employee = fields.Integer(compute="_compute_recruitment_stats")

    def _compute_new_applicant_count(self):
        self.new_applicant_count = 0
        if not self.env.user.has_group(
            "hr_recruitment.group_hr_recruitment_interviewer"
        ):
            return
        jobs = self.env["hr.job"].search([("department_id", "in", self.ids)])
        first_stage_by_job = self.env["hr.recruitment.stage"]._get_first_stage_by_job(
            jobs
        )
        counts = self.env["hr.applicant"]._read_group(
            [("job_id", "in", jobs.ids)], ["job_id", "stage_id"], ["__count"]
        )
        new_by_department = {}
        for job, stage, count in counts:
            if stage == first_stage_by_job[job]:
                new_by_department[job.department_id] = (
                    new_by_department.get(job.department_id, 0) + count
                )
        for department in self:
            department.new_applicant_count = new_by_department.get(department, 0)

    def _compute_recruitment_stats(self):
        job_data = self.env["hr.job"]._read_group(
            [("department_id", "in", self.ids)],
            ["department_id"],
            ["no_of_hired_employee:sum", "no_of_recruitment:sum"],
        )
        new_emp = {
            department.id: nb_employee for department, nb_employee, __ in job_data
        }
        expected_emp = {
            department.id: nb_recruitment for department, __, nb_recruitment in job_data
        }
        for department in self:
            department.new_hired_employee = new_emp.get(department.id, 0)
            department.expected_employee = expected_emp.get(department.id, 0)
