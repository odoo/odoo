import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

ENTITY_TYPES = [
    ("account", "Chart of Accounts"),
    ("partner", "Customers & Vendors"),
    ("invoice", "Invoices & Bills"),
    ("payment", "Payments & Transactions"),
    ("journal_entry", "Journal Entries"),
    ("product", "Products / Items"),
]


class QboCompanyMapping(models.Model):
    """Links one Odoo company to one QBO realm for synchronisation.

    Because some umbrella companies share a single QBO realm, this model
    supports the mixed layout: multiple Odoo companies can reference the
    same qbo.realm record. Each mapping carries its own entity toggles,
    sync schedule, and last-sync timestamp.
    """

    _name = "qbo.company.mapping"
    _description = "Odoo company ↔ QBO realm mapping"
    _order = "company_id, realm_id"
    _rec_name = "display_name"

    # ── Core link ─────────────────────────────────────────────────────────────
    company_id = fields.Many2one(
        "res.company",
        string="Odoo company",
        required=True,
        ondelete="cascade",
    )
    realm_id = fields.Many2one(
        "qbo.realm",
        string="QBO realm",
        required=True,
        ondelete="restrict",
    )

    display_name = fields.Char(compute="_compute_display_name", store=True)

    @api.depends("company_id", "realm_id")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.company_id.name} → {rec.realm_id.name}"

    # ── Sync toggles ──────────────────────────────────────────────────────────
    sync_enabled = fields.Boolean(string="Sync enabled", default=True)
    sync_accounts = fields.Boolean(string="Chart of Accounts", default=True)
    sync_partners = fields.Boolean(string="Customers & Vendors", default=True)
    sync_invoices = fields.Boolean(string="Invoices & Bills", default=True)
    sync_payments = fields.Boolean(string="Payments & Transactions", default=True)
    sync_journal_entries = fields.Boolean(string="Journal Entries", default=False)
    sync_products = fields.Boolean(string="Products / Items", default=True)

    # ── Timestamps ────────────────────────────────────────────────────────────
    last_sync_date = fields.Datetime(string="Last full sync", readonly=True)
    last_sync_accounts = fields.Datetime(string="Last accounts sync", readonly=True)
    last_sync_partners = fields.Datetime(string="Last partners sync", readonly=True)
    last_sync_invoices = fields.Datetime(string="Last invoices sync", readonly=True)
    last_sync_payments = fields.Datetime(string="Last payments sync", readonly=True)
    last_sync_journal_entries = fields.Datetime(string="Last JE sync", readonly=True)
    last_sync_products = fields.Datetime(string="Last products sync", readonly=True)

    # ── Schedule ──────────────────────────────────────────────────────────────
    sync_interval_minutes = fields.Integer(
        string="Sync interval (min)",
        default=60,
        help="Minimum minutes between automatic syncs. 0 = cron-only.",
    )

    # ── Stats ─────────────────────────────────────────────────────────────────
    conflict_count = fields.Integer(
        compute="_compute_conflict_count", string="Open conflicts"
    )
    log_count = fields.Integer(compute="_compute_log_count", string="Sync logs")

    def _compute_conflict_count(self):
        for rec in self:
            rec.conflict_count = self.env["qbo.conflict"].search_count(
                [("mapping_id", "=", rec.id), ("status", "=", "pending")]
            )

    def _compute_log_count(self):
        for rec in self:
            rec.log_count = self.env["qbo.sync.log"].search_count(
                [("mapping_id", "=", rec.id)]
            )

    # ── SQL constraint ─────────────────────────────────────────────────────────
    _unique_company_realm = models.Constraint(
        "UNIQUE(company_id, realm_id)",
        "An Odoo company can only have one mapping per QBO realm.",
    )

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_sync_now(self):
        """Trigger an immediate full sync for this mapping."""
        self.ensure_one()
        from ..services.qbo_sync_engine import QBOSyncEngine

        engine = QBOSyncEngine(self.env, self)
        engine.sync_all()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Sync complete"),
                "message": _("Sync finished for %s") % self.display_name,
                "type": "success",
            },
        }

    def action_view_conflicts(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Conflicts – %s") % self.display_name,
            "res_model": "qbo.conflict",
            "view_mode": "list,form",
            "domain": [("mapping_id", "=", self.id), ("status", "=", "pending")],
        }

    def action_view_logs(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Sync log – %s") % self.display_name,
            "res_model": "qbo.sync.log",
            "view_mode": "list",
            "domain": [("mapping_id", "=", self.id)],
        }

    # ── Timestamp helper used by the sync engine ──────────────────────────────

    def get_last_sync_for(self, entity_type):
        """Return the datetime of the last successful sync for a given entity type."""
        field_map = {
            "account": "last_sync_accounts",
            "partner": "last_sync_partners",
            "invoice": "last_sync_invoices",
            "payment": "last_sync_payments",
            "journal_entry": "last_sync_journal_entries",
            "product": "last_sync_products",
        }
        fname = field_map.get(entity_type)
        return getattr(self, fname, False) if fname else False

    def set_last_sync_for(self, entity_type):
        """Stamp the last sync time for a given entity type."""
        field_map = {
            "account": "last_sync_accounts",
            "partner": "last_sync_partners",
            "invoice": "last_sync_invoices",
            "payment": "last_sync_payments",
            "journal_entry": "last_sync_journal_entries",
            "product": "last_sync_products",
        }
        fname = field_map.get(entity_type)
        if fname:
            self.write({fname: fields.Datetime.now(), "last_sync_date": fields.Datetime.now()})
