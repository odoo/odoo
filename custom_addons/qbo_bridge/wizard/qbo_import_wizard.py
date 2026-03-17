import base64
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..services.qbo_file_parser import QBOFileParser, QBOFileParseError
from ..services.qbo_sync_engine import QBOSyncEngine

_logger = logging.getLogger(__name__)

ENTITY_CHOICES = [
    ("account", "Chart of Accounts"),
    ("partner", "Customers & Vendors"),
    ("invoice", "Invoices & Bills"),
    ("payment", "Payments & Transactions"),
    ("journal_entry", "Journal Entries"),
    ("product", "Products / Items"),
]

FILE_TYPE_CHOICES = [
    ("csv", "CSV (.csv)"),
    ("xlsx", "Excel (.xlsx)"),
    ("json", "JSON (.json)"),
]


class QboImportWizard(models.TransientModel):
    """Wizard for importing QBO file exports as the API fallback.

    Opens from the QBO Bridge menu. The user selects a mapping, entity type,
    and uploads the file. The wizard calls QBOFileParser → QBOSyncEngine.
    """

    _name = "qbo.import.wizard"
    _description = "QBO file import wizard"

    mapping_id = fields.Many2one(
        "qbo.company.mapping",
        string="Mapping",
        required=True,
        domain=[("sync_enabled", "=", True)],
    )
    company_id = fields.Many2one(
        related="mapping_id.company_id", readonly=True, string="Company"
    )
    realm_id = fields.Many2one(
        related="mapping_id.realm_id", readonly=True, string="Realm"
    )

    entity_type = fields.Selection(
        ENTITY_CHOICES,
        string="Entity type",
        required=True,
        default="account",
    )
    file_type = fields.Selection(
        FILE_TYPE_CHOICES,
        string="File type",
        required=True,
        default="csv",
    )
    import_file = fields.Binary(string="File", required=True, attachment=False)
    filename = fields.Char(string="Filename")

    # ── Result summary shown after import ─────────────────────────────────────
    result_message = fields.Text(string="Result", readonly=True)
    state = fields.Selection(
        [("ready", "Ready"), ("done", "Done")], default="ready"
    )

    @api.onchange("filename")
    def _onchange_filename(self):
        """Auto-detect file type from extension."""
        if self.filename:
            ext = self.filename.rsplit(".", 1)[-1].lower()
            for choice, _ in FILE_TYPE_CHOICES:
                if choice == ext:
                    self.file_type = choice
                    break

    def action_import(self):
        self.ensure_one()
        if not self.import_file:
            raise UserError(_("Please upload a file before importing."))

        raw = base64.b64decode(self.import_file)
        parser = QBOFileParser()
        try:
            records = parser.parse(raw, self.file_type, self.entity_type)
        except QBOFileParseError as exc:
            raise UserError(_("File parse error: %s") % exc) from exc

        if not records:
            self.result_message = _("No records found in the uploaded file.")
            self.state = "done"
            return self._stay_open()

        engine = QBOSyncEngine(self.env, self.mapping_id)
        try:
            engine.sync_from_file(records, self.entity_type)
        except Exception as exc:
            raise UserError(_("Import failed: %s") % exc) from exc

        stats = engine._stats
        self.result_message = _(
            "Import complete.\n"
            "Created: %(created)s  |  Updated: %(updated)s  |  "
            "Skipped: %(skipped)s  |  Conflicts: %(conflicts)s  |  Errors: %(errors)s"
        ) % stats
        self.state = "done"
        return self._stay_open()

    def _stay_open(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
