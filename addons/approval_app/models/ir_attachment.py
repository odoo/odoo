from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.approval.models import approval_trace as trace


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    approval_requirement_id = fields.Many2one(
        comodel_name="approval.document.requirement",
        string="Satisfies Requirement",
        index="btree_not_null",
        ondelete="set null",
        help="Which of the category's required documents this file IS. The "
        "requester says so; nothing infers it. Before this column the "
        "confirm-time check ran a bipartite matching over file NAMES, "
        "which cannot express the invariant it was asked to enforce: a "
        "file called 'holiday-photo-not-an-invoice.png' satisfied a "
        "requirement named 'Invoice', and a genuine invoice scanned to "
        "'scan001.pdf' did not.",
    )

    @api.constrains("approval_requirement_id", "res_model", "res_id")
    def _check_approval_requirement_belongs_to_the_request(self) -> None:
        for attachment in self.filtered("approval_requirement_id"):
            if attachment.res_model != "approval.request" or not attachment.res_id:
                trace.REFUSAL.event(
                    "requirement_not_on_a_request",
                    attachment=attachment.id,
                    model=attachment.res_model,
                    res_id=attachment.res_id,
                )
                raise ValidationError(
                    self.env._(
                        "Only a file attached to an approval request can "
                        "satisfy one of its document requirements.",
                    ),
                )
            request = self.env["approval.request"].sudo().browse(attachment.res_id)
            if attachment.approval_requirement_id.category_id != request.category_id:
                trace.REFUSAL.event(
                    "requirement_of_other_category",
                    attachment=attachment.id,
                    requirement=attachment.approval_requirement_id.id,
                    request=request.id,
                )
                raise ValidationError(
                    self.env._(
                        "'%(requirement)s' is a document requirement of "
                        "category '%(other)s', not of this request's "
                        "category '%(category)s'.",
                        requirement=attachment.approval_requirement_id.name,
                        other=attachment.approval_requirement_id.category_id.name,
                        category=request.category_id.name,
                    ),
                )

    def write(self, vals):
        if "approval_requirement_id" in vals:
            requests = self._approval_attachments_in_self().mapped("res_id")
            if self._approval_terminal_parent_ids(set(requests)):
                trace.REFUSAL.event(
                    "requirement_of_decided_request",
                    attachments=self.ids,
                    requests=sorted(set(requests)),
                )
                raise UserError(
                    self.env._(
                        "You cannot change which requirement a document satisfies "
                        "once its approval request is approved, refused or "
                        "cancelled.",
                    ),
                )
        return super().write(vals)
