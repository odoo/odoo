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
    publish_after_import = fields.Boolean(
        string="Publish detail accounts to a company chart",
        default=True,
    )
    publish_company_id = fields.Many2one(
        "res.company",
        string="Publish to company",
        default=lambda self: self.env.company,
    )
    update_existing_company_accounts = fields.Boolean(
        string="Update existing company accounts",
        default=True,
    )
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

        publish_stats = None
        if self.publish_after_import:
            if not self.publish_company_id:
                raise UserError(_("Choose the company that should receive the native chart."))
            publish_stats = StandardAccount.sync_detail_accounts_to_company(
                self.publish_company_id,
                update_existing=self.update_existing_company_accounts,
            )

        message = _(
            "Import complete.\n"
            "Created: %(created)s\n"
            "Updated: %(updated)s\n"
            "Parents linked: %(parents_linked)s",
        ) % stats
        if publish_stats:
            message += _(
                "\n\nNative chart publish complete for %(company)s.\n"
                "Company accounts created: %(created)s\n"
                "Company accounts updated: %(updated)s\n"
                "Company accounts skipped: %(skipped)s",
            ) % {
                "company": self.publish_company_id.display_name,
                "created": publish_stats["created"],
                "updated": publish_stats["updated"],
                "skipped": publish_stats["skipped"],
            }
        self.result_message = message
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
