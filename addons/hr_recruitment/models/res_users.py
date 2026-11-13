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
        officers_before = self.filtered(lambda u: officer_group in u.group_ids)
        interviewers_before = self.filtered(lambda u: interviewer_group in u.group_ids)

        result = super().write(vals)

        lost_officers = officers_before.filtered(lambda u: officer_group not in u.group_ids)
        lost_interviewers = interviewers_before.filtered(lambda u: interviewer_group not in u.group_ids)

        if lost_officers:
            employees = self.env["hr.employee"].search([("user_id", "in", self.ids)])
            self.env["hr.job"].sudo().search(
                [("recruiter_id", "in", employees.ids)],
            ).write({"recruiter_id": False})

        if lost_interviewers:
            commands = [Command.unlink(uid) for uid in self.ids]
            for model in ("hr.job", "hr.applicant"):
                self.env[model].sudo().search(
                    [("interviewer_ids", "in", self.ids)],
                ).write({"interviewer_ids": commands})

        return result
