# Copyright (C) 2013 Savoir-faire Linux (<http://www.savoirfairelinux.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval


class DocumentPage(models.Model):
    """Useful to know the state of a document."""

    _inherit = "document.page"

    history_ids = fields.One2many(domain=[("state", "=", "approved")])

    approved_date = fields.Datetime(
        "Approved Date",
        related="history_head.approved_date",
        store=True,
        index=True,
    )

    approved_uid = fields.Many2one(
        "res.users",
        "Approved by",
        related="history_head.approved_uid",
        store=True,
        index=True,
    )

    approval_required = fields.Boolean(
        "Require approval",
        help="Require approval for changes on this page or its child pages.",
    )

    approver_gid = fields.Many2one(
        "res.groups",
        "Approver group",
        help="Users must also belong to the Approvers group",
    )

    is_approval_required = fields.Boolean(
        "Approval required",
        help="If true, changes of this page require approval",
        compute="_compute_is_approval_required",
        recursive=True,
    )

    am_i_approver = fields.Boolean(compute="_compute_am_i_approver")

    approver_group_ids = fields.Many2many(
        "res.groups",
        string="Approver groups",
        help="Groups that can approve changes to this document",
        compute="_compute_approver_group_ids",
        recursive=True,
    )

    # pylint: disable=W8113
    has_changes_pending_approval = fields.Boolean(
        compute="_compute_has_changes_pending_approval",
        string="Has changes pending approval",
    )

    user_has_drafts = fields.Boolean(
        compute="_compute_user_has_drafts", string="User has drafts?"
    )

    def _valid_field_parameter(self, field, name):
        return name == "order" or super()._valid_field_parameter(field, name)

    @api.depends("approval_required", "parent_id.is_approval_required")
    def _compute_is_approval_required(self):
        """Check if the document required approval based on his parents."""
        for page in self:
            res = page.approval_required
            if page.parent_id:
                res = res or page.parent_id.is_approval_required
            page.is_approval_required = res

    @api.depends("approver_gid", "parent_id.approver_group_ids")
    def _compute_approver_group_ids(self):
        """Compute the approver groups based on his parents."""
        for page in self:
            res = page.approver_gid
            if page.parent_id:
                res = res | page.parent_id.approver_group_ids
            page.approver_group_ids = res

    @api.depends("is_approval_required", "approver_group_ids")
    def _compute_am_i_approver(self):
        """Check if the current user can approve changes to this page."""
        for rec in self:
            rec.am_i_approver = rec.can_user_approve_this_page(self.env.user)

    def can_user_approve_this_page(self, user):
        """Check if a user can approve this page."""
        self.ensure_one()
        # if it's not required, anyone can approve
        if not self.is_approval_required:
            return True
        # if user belongs to 'Knowledge / Manager', he can approve anything
        if user.has_group("document_page.group_document_manager"):
            return True
        # to approve, user must have approver rights
        if not user.has_group("document_page_approval.group_document_approver_user"):
            return False
        # if there aren't any approver_groups_defined, user can approve
        if not self.approver_group_ids:
            return True
        # to approve, user must belong to any of the approver groups
        return len(user.group_ids & self.approver_group_ids) > 0

    def _compute_has_changes_pending_approval(self):
        history = self.env["document.page.history"]
        for rec in self:
            changes = history.search_count(
                [("page_id", "=", rec.id), ("state", "=", "to approve")]
            )
            rec.has_changes_pending_approval = changes > 0

    def _compute_user_has_drafts(self):
        history = self.env["document.page.history"]
        for rec in self:
            changes = history.search_count(
                [("page_id", "=", rec.id), ("state", "=", "draft")]
            )
            rec.user_has_drafts = changes > 0

    def _create_history(self, vals):
        res = super()._create_history(vals)
        res.action_to_approve()
        return res

    def action_changes_pending_approval(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "document_page_approval.action_change_requests"
        )
        context = safe_eval(action["context"])
        context["search_default_page_id"] = self.id
        context["default_page_id"] = self.id
        action["context"] = context
        return action
