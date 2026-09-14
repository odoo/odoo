from odoo import Command, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ResUsers(models.Model):
    _inherit = "res.users"

    def _is_recruitment_interviewer_only(self):
        self.check_singleton()
        return self.has_group(
            "hr_recruitment.group_hr_recruitment_interviewer"
        ) and not self.has_group("hr_recruitment.group_hr_recruitment_user")

    def _create_recruitment_interviewers(self):
        if not self:
            return
        interviewer_group = self.env.ref(
            "hr_recruitment.group_hr_recruitment_interviewer"
        )
        recruitment_group = self.env.ref("hr_recruitment.group_hr_recruitment_user")

        interviewers = self - recruitment_group.all_user_ids
        _debug.lifecycle(
            "interviewer_group_granted",
            candidates=self,
            granted=interviewers,
            already_recruiters=len(self) - len(interviewers),
        )
        interviewers.sudo().write({"group_ids": [Command.link(interviewer_group.id)]})

    def _remove_recruitment_interviewers(self):
        if not self:
            return
        interviewer_group = self.env.ref(
            "hr_recruitment.group_hr_recruitment_interviewer"
        )
        recruitment_group = self.env.ref("hr_recruitment.group_hr_recruitment_user")

        job_interviewers = self.env["hr.job"]._read_group(
            [("interviewer_ids", "in", self.ids)], ["interviewer_ids"]
        )
        user_ids = {interviewer.id for [interviewer] in job_interviewers}

        application_interviewers = self.env["hr.applicant"]._read_group(
            [("interviewer_ids", "in", self.ids)], ["interviewer_ids"]
        )
        user_ids |= {interviewer.id for [interviewer] in application_interviewers}

        users_to_remove = set(self.ids) - (
            user_ids | set(recruitment_group.all_user_ids.ids)
        )
        _debug.lifecycle(
            "interviewer_group_revoked",
            candidates=self,
            revoked=len(users_to_remove),
            still_interviewing=len(set(self.ids) & user_ids),
        )
        self.env["res.users"].browse(users_to_remove).sudo().write(
            {"group_ids": [Command.unlink(interviewer_group.id)]}
        )
