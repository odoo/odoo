from odoo import api, models
from odoo.exceptions import UserError

from . import approval_trace as trace

_APPROVAL_LOCKED_FIELDS = frozenset(
    {
        "name",
        "description",
        "datas",
        "raw",
        "mimetype",
        "type",
        "url",
        "res_model",
        "res_id",
        "res_field",
    },
)


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def _approval_terminal_parent_ids(self, request_ids):
        if not request_ids:
            return set()
        terminal = self.env["approval.request"]._TERMINAL_STATES
        requests = self.env["approval.request"].sudo().browse(list(request_ids))
        return {r.id for r in requests if r.exists() and r.state in terminal}

    def _approval_res_field_is_real(self, res_model, res_field) -> bool:
        if not res_field:
            return False
        model = self.env.get(res_model)
        if model is None:
            return False
        field = model._fields.get(res_field)
        return bool(
            field
            and field.type == "binary"
            and field.store
            and getattr(field, "attachment", False)
        )

    def _approval_attachments_in_self(self):
        if not self:
            return self.browse()
        return self.sudo().filtered(
            lambda a: (
                a.res_model == "approval.request"
                and not self._approval_res_field_is_real(a.res_model, a.res_field)
            ),
        )

    @api.model_create_multi
    def create(self, vals_list):
        candidate_ids = {
            vals.get("res_id")
            for vals in vals_list
            if vals.get("res_model") == "approval.request"
            and not self._approval_res_field_is_real(
                vals.get("res_model"),
                vals.get("res_field"),
            )
            and vals.get("res_id")
        }
        if self._approval_terminal_parent_ids(candidate_ids):
            trace.REFUSAL.event(
                "attach_to_decided_request",
                requests=sorted(candidate_ids),
                uid=self.env.uid,
            )
            raise UserError(
                self.env._(
                    "You cannot attach a document to an approval request "
                    "that has been approved, refused or cancelled.",
                ),
            )
        return super().create(vals_list)

    def write(self, vals):
        if not vals.keys() & _APPROVAL_LOCKED_FIELDS:
            return super().write(vals)
        targeted = self._approval_attachments_in_self()
        blocked_ids = set(targeted.mapped("res_id"))
        if {"res_model", "res_id", "res_field"} & vals.keys():
            for att in self.sudo():
                new_model = vals.get("res_model", att.res_model)
                new_id = vals.get("res_id", att.res_id)
                new_field = vals.get("res_field", att.res_field)
                if (
                    new_model == "approval.request"
                    and new_id
                    and not self._approval_res_field_is_real(new_model, new_field)
                ):
                    blocked_ids.add(new_id)
        if self._approval_terminal_parent_ids(blocked_ids):
            trace.REFUSAL.event(
                "write_attachment_of_decided_request",
                attachments=self.ids,
                requests=sorted(blocked_ids),
                fields=sorted(vals.keys() & _APPROVAL_LOCKED_FIELDS),
            )
            raise UserError(
                self.env._(
                    "You cannot modify an attachment linked to an approval "
                    "request that has been approved, refused or cancelled.",
                ),
            )
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_approved_approval_request(self):
        targeted = self._approval_attachments_in_self()
        if targeted and self._approval_terminal_parent_ids(targeted.mapped("res_id")):
            trace.REFUSAL.event(
                "unlink_attachment_of_decided_request",
                attachments=targeted.ids,
                uid=self.env.uid,
            )
            raise UserError(
                self.env._(
                    "You cannot unlink an attachment which is linked to an "
                    "approved, refused or cancelled approval request.",
                ),
            )
