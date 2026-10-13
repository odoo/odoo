# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _create_recruitment_interviewers(self):
        if not self:
            return
        interviewer_group = self.env.ref('hr_recruitment.group_hr_recruitment_interviewer')
        recruitment_group = self.env.ref('hr_recruitment.group_hr_recruitment_user')

        interviewers = self - recruitment_group.all_user_ids
        interviewers.sudo().write({
            'group_ids': [(4, interviewer_group.id)]
        })

    def _remove_recruitment_interviewers(self):
        if not self:
            return
        interviewer_group = self.env.ref('hr_recruitment.group_hr_recruitment_interviewer')
        recruitment_group = self.env.ref('hr_recruitment.group_hr_recruitment_user')

        job_interviewers = self.env['hr.job']._read_group([('interviewer_ids', 'in', self.ids)], ['interviewer_ids'])
        user_ids = {interviewer.id for [interviewer] in job_interviewers}

        application_interviewers = self.env['hr.applicant']._read_group([('interviewer_ids', 'in', self.ids)], ['interviewer_ids'])
        user_ids |= {interviewer.id for [interviewer] in application_interviewers}

        # Remove users that are no longer interviewers on at least a job or an application
        users_to_remove = set(self.ids) - (user_ids | set(recruitment_group.all_user_ids.ids))
        self.env['res.users'].browse(users_to_remove).sudo().write({
            'group_ids': [(3, interviewer_group.id)]
        })

    def write(self, vals):
        officer_group = self.env.ref("hr_recruitment.group_hr_recruitment_user")
        interviewer_group = self.env.ref("hr_recruitment.group_hr_recruitment_interviewer")
        officers_before = self.filtered(lambda u: officer_group in u.all_group_ids)
        interviewers_before = self.filtered(lambda u: interviewer_group in u.all_group_ids)

        result = super().write(vals)

        lost_officers = officers_before.filtered(lambda u: officer_group not in u.all_group_ids)
        lost_interviewers = interviewers_before.filtered(lambda u: interviewer_group not in u.all_group_ids)
        if not (lost_officers or lost_interviewers):
            return result

        env = self.sudo().with_context(active_test=False).env
        if lost_officers:
            employees = env["hr.employee"].search([("user_id", "in", lost_officers.ids)])
            if employees:
                for model in ("hr.job", "hr.applicant"):
                    env[model].search(
                        [("recruiter_id", "in", employees.ids)],
                    ).write({"recruiter_id": False})

        if lost_interviewers:
            commands = [Command.unlink(uid) for uid in lost_interviewers.ids]
            for model in ("hr.job", "hr.applicant"):
                env[model].search(
                    [("interviewer_ids", "in", lost_interviewers.ids)],
                ).write({"interviewer_ids": commands})

        return result
