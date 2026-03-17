import base64

from odoo import _, fields, models
from odoo.exceptions import UserError


class QboStandardChartImportWizard(models.TransientModel):
    _name = "qbo.standard.chart.import.wizard"
    _description = "Import standard chart"

    import_source = fields.Selection(
        [
            ("bundled", "Bundled standard chart"),
            ("upload", "Upload CSV"),
        ],
        default="bundled",
        required=True,
    )
    import_file = fields.Binary(string="CSV file")
    filename = fields.Char()
    result_message = fields.Text(readonly=True)
    state = fields.Selection(
        [("ready", "Ready"), ("done", "Done")],
        default="ready",
    )

    def action_import(self):
        self.ensure_one()
        StandardAccount = self.env["qbo.standard.account"]
        if self.import_source == "bundled":
            stats = StandardAccount.import_bundled_chart()
        else:
            if not self.import_file:
                raise UserError(_("Upload the CSV file before importing."))
            stats = StandardAccount.import_chart_from_bytes(base64.b64decode(self.import_file))

        self.result_message = _(
            "Import complete.\n"
            "Created: %(created)s\n"
            "Updated: %(updated)s\n"
            "Parents linked: %(parents_linked)s",
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
