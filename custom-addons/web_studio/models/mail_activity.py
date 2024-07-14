from odoo import models
from odoo.exceptions import UserError


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def _action_done(self, feedback=False, attachment_ids=False):
        approval_activities = self.filtered(lambda a: a.activity_category == 'grant_approval')
        if approval_activities:
            ApprovalRequestSudo = self.env["studio.approval.request"].sudo()
            approval_requests = ApprovalRequestSudo.search([("mail_activity_id", "in", approval_activities.ids)])
            for activity in approval_activities:
                res_id = activity.res_id
                request = approval_requests.filtered(lambda r: r.mail_activity_id == activity)
                if not request:
                    continue
                try:
                    request.rule_id.with_context(
                        prevent_approval_request_unlink=True
                    ).set_approval(res_id, True)
                except UserError:
                    # the rule has already been rejected/approved or the user does not enough enough rights (or has
                    # already approved exclusive rules) and is trying to "mark ad done" for another user
                    # this should not prevent the user from marking this as done and should not modify any
                    # approval entry
                    # this means that if another user marks this as done and they have "all the rights" necessary
                    # to approve the action, then their approval will be accepted (under their own name)
                    pass
        return super()._action_done(feedback=feedback, attachment_ids=attachment_ids)
