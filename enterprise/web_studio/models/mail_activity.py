import contextlib

from odoo import models
from odoo.exceptions import UserError
from odoo.osv import expression


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def _action_done(self, feedback=False, attachment_ids=False):
        approval_activities = self.filtered(lambda a: a.activity_category == 'grant_approval')
        if approval_activities:
            ApprovalRequestSudo = self.env["studio.approval.request"].sudo()
            approval_requests = ApprovalRequestSudo.search([("mail_activity_id", "in", approval_activities.ids)])
            domains = []
            pairs = set()
            for request in approval_requests:
                pairs.add((request.res_id, request.rule_id))
                domains.append([
                    "&",
                    ("res_id", "=", request.res_id),
                    ("rule_id", "=", request.rule_id.id)
                ])
            domain = expression.OR(domains)
            extra_activities_to_mark_as_done = ApprovalRequestSudo.search(domain).mail_activity_id - approval_activities
            extra_activities_to_mark_as_done = self.env['mail.activity'].browse(extra_activities_to_mark_as_done.ids)
            super(MailActivity, extra_activities_to_mark_as_done)._action_done(feedback=feedback, attachment_ids=attachment_ids)
            for (res_id, rule) in pairs:
                with contextlib.suppress(UserError):
                    # the rule has already been rejected/approved or the user does not enough enough rights (or has
                    # already approved exclusive rules) and is trying to "mark ad done" for another user
                    # this should not prevent the user from marking this as done and should not modify any
                    # approval entry
                    # this means that if another user marks this as done and they have "all the rights" necessary
                    # to approve the action, then their approval will be accepted (under their own name)
                    rule.with_context(
                        prevent_approval_request_unlink=True
                    ).set_approval(res_id, True)
        return super()._action_done(feedback=feedback, attachment_ids=attachment_ids)
