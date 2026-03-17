from odoo import fields, models


class QboSyncLog(models.Model):
    """Immutable audit log written by QBOSyncEngine for every sync operation.

    One record per entity-level operation (create / update / skip / conflict).
    Never edited after creation; used for debugging and compliance.
    """

    _name = "qbo.sync.log"
    _description = "QBO sync log"
    _order = "sync_date desc, id desc"

    mapping_id = fields.Many2one(
        "qbo.company.mapping",
        string="Mapping",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        related="mapping_id.company_id", store=True, string="Company", readonly=True
    )
    realm_id = fields.Many2one(
        related="mapping_id.realm_id", store=True, string="Realm", readonly=True
    )

    sync_date = fields.Datetime(string="Date", default=fields.Datetime.now, index=True)

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

    direction = fields.Selection(
        [
            ("pull", "QBO → Odoo"),
            ("push", "Odoo → QBO"),
            ("conflict", "Conflict flagged"),
        ],
        string="Direction",
        required=True,
    )

    status = fields.Selection(
        [
            ("success", "Success"),
            ("skipped", "Skipped (no change)"),
            ("conflict", "Conflict"),
            ("error", "Error"),
        ],
        string="Status",
        required=True,
    )

    qbo_id = fields.Char(string="QBO ID", index=True)
    odoo_model = fields.Char(string="Odoo model")
    odoo_record_id = fields.Integer(string="Odoo record ID")
    odoo_record_ref = fields.Char(
        string="Odoo record",
        compute="_compute_odoo_record_ref",
        store=False,
    )

    message = fields.Text(string="Message / error")
    duration_ms = fields.Integer(string="Duration (ms)")

    # ── Computed display link to Odoo record ─────────────────────────────────

    def _compute_odoo_record_ref(self):
        for rec in self:
            if rec.odoo_model and rec.odoo_record_id:
                try:
                    obj = self.env[rec.odoo_model].browse(rec.odoo_record_id)
                    rec.odoo_record_ref = obj.display_name if obj.exists() else str(rec.odoo_record_id)
                except Exception:
                    rec.odoo_record_ref = str(rec.odoo_record_id)
            else:
                rec.odoo_record_ref = False

    # ── Convenience factory ───────────────────────────────────────────────────

    @classmethod
    def log(cls, env, mapping, entity_type, direction, status, *, qbo_id=None,
            odoo_model=None, odoo_record_id=None, message=None, duration_ms=None):
        """Shorthand to create a log entry from the sync engine."""
        env["qbo.sync.log"].sudo().create({
            "mapping_id": mapping.id,
            "entity_type": entity_type,
            "direction": direction,
            "status": status,
            "qbo_id": qbo_id,
            "odoo_model": odoo_model,
            "odoo_record_id": odoo_record_id,
            "message": message,
            "duration_ms": duration_ms,
        })
