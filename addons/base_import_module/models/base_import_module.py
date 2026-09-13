import base64
import logging
from io import BytesIO

from odoo import fields, models

_logger = logging.getLogger(__name__)


class BaseImportModule(models.TransientModel):
    """Wizard to upload and install a module from an uploaded zip archive."""

    _name = "base.import.module"
    _description = "Import Module"

    module_file = fields.Binary(
        string="Module .ZIP file",
        attachment=False,
        required=True,
    )
    state = fields.Selection(
        selection=[("init", "init"), ("done", "done")],
        string="Status",
        default="init",
        readonly=True,
    )
    import_message = fields.Text()
    force = fields.Boolean(
        string="Force init",
        help="Force init mode even if installed. (will update `noupdate='1'` records)",
    )
    with_demo = fields.Boolean(string="Import demo data of module")
    modules_dependencies = fields.Text()

    def import_module(self):
        self.check_singleton()
        IrModule = self.env["ir.module.module"]
        zip_data = base64.decodebytes(self.module_file)
        fp = BytesIO()
        fp.write(zip_data)
        _message, module_names = IrModule._import_zipfile(
            fp, force=self.force, with_demo=self.with_demo
        )
        # `state`/`import_message` are never set to 'done' here, so the form
        # view's whole "done" branch is dead (t24068 gap, report-only — the
        # redirect-away-on-success UX may be intentional; see the audit shard
        # for the fuller "show a real success message" option). At minimum,
        # log what was imported so it's not silently discarded.
        _logger.info(
            "Imported modules from zip: %s", ", ".join(module_names) or "(none)"
        )
        return {
            "type": "ir.actions.act_url",
            "target": "self",
            "url": "/odoo",
        }

    def get_dependencies_to_install_names(self):
        module_ids, _not_found = self.env[
            "ir.module.module"
        ]._get_missing_dependencies_modules(base64.decodebytes(self.module_file))
        return module_ids.mapped("name")

    def action_module_open(self):
        self.check_singleton()
        return {
            "domain": [("name", "in", self.env.context.get("module_name", []))],
            "name": "Modules",
            "view_mode": "list,form",
            "res_model": "ir.module.module",
            "view_id": False,
            "type": "ir.actions.act_window",
        }
