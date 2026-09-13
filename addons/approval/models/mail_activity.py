from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain

from . import approval_trace as trace
from odoo.addons.mail.tools.discuss import Store


class MailActivity(models.Model):
    _inherit = "mail.activity"

    approval_request_id = fields.Many2one(
        comodel_name="approval.request",
        compute="_compute_approval_request_id",
        search="_search_approval_request_id",
    )
    approver_id = fields.Many2one(
        comodel_name="approval.approver",
        index="btree_not_null",
        ondelete="cascade",
        help="The approver row this activity asks. Stored when the engine creates the "
        "activity, so the activity is an approval wherever it lives -- on the request "
        "or on the document it approves.",
    )

    @api.depends("approver_id")
    def _compute_approval_request_id(self):
        for activity in self:
            activity.approval_request_id = activity.approver_id.request_id

    def _search_approval_request_id(self, operator, value):
        if operator in Domain.NEGATIVE_OPERATORS:
            trace.REFUSAL.event("negative_operator_unsupported", operator=operator)
            raise UserError(
                self.env._(
                    "Negative operators (%(operator)s) are not supported for "
                    "searching by approval_request_id. Use positive operators instead.",
                    operator=operator,
                )
            )
        if operator == "any":
            operator = "in"
            if isinstance(value, Domain):
                value = self.env["approval.request"]._search(value)
        return [("approver_id.request_id", operator, value)]

    def _action_done(self, feedback=False, attachment_ids=None):
        approvers = self._get_answering_approvers()
        trace.ACTIVITY.event(
            "done",
            activities=self.ids,
            uid=self.env.uid,
            approves=approvers.ids,
        )
        if not approvers:
            return super()._action_done(
                feedback=feedback, attachment_ids=attachment_ids
            )
        with self.env.cr.savepoint():
            result = super()._action_done(
                feedback=feedback, attachment_ids=attachment_ids
            )
            for approver in approvers:
                approver.action_approve()
        return result

    def _get_answering_approvers(self):
        """The rows these activities approve when marked done.

        Done by the approver it was asked of, an approval activity approves; anyone else
        marking it done only dismisses it. The approval follows the done, so the
        feedback given with it is posted rather than closed over by the decision, and
        both run in one savepoint, so a decision that cannot be recorded raises and
        leaves the activity open rather than done with nothing decided.
        """
        user = self.env.user
        return self.filtered(
            lambda activity: (
                activity.active
                and activity.approver_id
                and activity.user_id == user
                and activity.user_id == activity.approver_id._get_effective_approver()
            )
        ).approver_id.filtered(
            lambda approver: (
                approver.state == "pending" and approver.request_id.state == "pending"
            )
        )

    def _to_store_defaults(self, target):
        return super()._to_store_defaults(target) + [
            Store.One("approver_id", ["state"]),
        ]
