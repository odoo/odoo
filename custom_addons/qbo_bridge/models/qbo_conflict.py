import json

from odoo import _, api, fields, models


class QboConflict(models.Model):
    """Records a data conflict when both Odoo and QBO have changed the same entity
    since the last successful sync.

    The reconciliation UI presents both versions side by side and lets the user
    choose which side wins, or skip the conflict entirely.
    """

    _name = "qbo.conflict"
    _description = "QBO sync conflict"
    _order = "create_date desc"

    mapping_id = fields.Many2one(
        "qbo.company.mapping",
        string="Mapping",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        related="mapping_id.company_id", store=True, readonly=True
    )
    realm_id = fields.Many2one(
        related="mapping_id.realm_id", store=True, readonly=True
    )

    entity_type = fields.Selection(
        [
            ("account", "Chart of Accounts"),
            ("partner", "Customers & Vendors"),
            ("invoice", "Invoices & Bills"),
            ("payment", "Payments & Transactions"),
            ("journal_entry", "Journal Entries"),
            ("product", "Products / Items"),
        ],
        string="Entity type",
        required=True,
    )

    qbo_id = fields.Char(string="QBO ID", required=True, index=True)
    odoo_model = fields.Char(string="Odoo model")
    odoo_record_id = fields.Integer(string="Odoo record ID")

    # ── Snapshot of both sides at conflict detection time ─────────────────────
    odoo_data = fields.Text(
        string="Odoo version (JSON)",
        help="JSON snapshot of the Odoo record at conflict detection time.",
    )
    qbo_data = fields.Text(
        string="QBO version (JSON)",
        help="JSON snapshot of the QBO record at conflict detection time.",
    )
    odoo_write_date = fields.Datetime(string="Odoo last modified")
    qbo_last_updated = fields.Datetime(string="QBO last updated")

    # ── Computed diff summary shown in the list view ──────────────────────────
    diff_summary = fields.Text(
        compute="_compute_diff_summary",
        string="Changed fields",
        store=False,
    )

    @api.depends("odoo_data", "qbo_data")
    def _compute_diff_summary(self):
        for rec in self:
            try:
                odoo = json.loads(rec.odoo_data or "{}")
                qbo = json.loads(rec.qbo_data or "{}")
                changed = [k for k in set(list(odoo) + list(qbo)) if odoo.get(k) != qbo.get(k)]
                rec.diff_summary = ", ".join(changed[:10]) or _("No differences detected")
            except Exception:
                rec.diff_summary = _("Could not parse diff")

    # ── Resolution ────────────────────────────────────────────────────────────
    status = fields.Selection(
        [
            ("pending", "Pending review"),
            ("resolved_odoo", "Resolved — Odoo won"),
            ("resolved_qbo", "Resolved — QBO won"),
            ("skipped", "Skipped"),
        ],
        default="pending",
        string="Status",
        index=True,
    )
    resolved_by = fields.Many2one("res.users", string="Resolved by", readonly=True)
    resolved_date = fields.Datetime(string="Resolved on", readonly=True)
    resolution_notes = fields.Text(string="Notes")

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_open_resolve_wizard(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Resolve conflict"),
            "res_model": "qbo.conflict.resolve.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_conflict_id": self.id},
        }

    def action_open_odoo_record(self):
        self.ensure_one()
        if self.odoo_model and self.odoo_record_id:
            return {
                "type": "ir.actions.act_window",
                "res_model": self.odoo_model,
                "res_id": self.odoo_record_id,
                "view_mode": "form",
                "target": "new",
            }

    # ── Internal helper ───────────────────────────────────────────────────────

    def _mark_resolved(self, resolution, notes=None):
        """Called by the resolve wizard or the sync engine."""
        self.write(
            {
                "status": resolution,
                "resolved_by": self.env.uid,
                "resolved_date": fields.Datetime.now(),
                "resolution_notes": notes,
            }
        )
