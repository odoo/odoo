from odoo import _, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class CustomerStatementCustomHandler(models.AbstractModel):
    _name = "account.customer.statement.report.handler"
    _inherit = "account.partner.ledger.report.handler"
    _description = "Customer Statement Custom Handler"

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)

        options["buttons"].append(
            {
                "name": _("Send"),
                "action": "action_send_statements",
                "sequence": 90,
                "always_show": True,
            }
        )
        options["custom_display_config"]["css_custom_class"] += " customer_statement"
        options["custom_display_config"]["components"]["AccountReportLine"] = (
            "PartnerLedgerFollowupLine"
        )
        options["custom_display_config"]["templates"]["AccountReportHeader"] = (
            "account.PartnerLedgerFollowupHeader"
        )

        if self.env.ref(
            "account.pdf_export_main_customer_report", raise_if_not_found=False
        ):
            options["custom_display_config"].setdefault("pdf_export", {})[
                "pdf_export_main"
            ] = "account.pdf_export_main_customer_report"

    @_debug.perf.timed
    def action_send_statements(self, options):
        _debug.lifecycle("action_send_statements", records=self)
        template = self.env.ref("account.email_template_customer_statement", False)
        partners = self.env["res.partner"].browse(options.get("partner_ids", []))
        return {
            "name": _("Send %s Statement", partners.name)
            if len(partners) == 1
            else _("Send Partner Ledgers"),
            "type": "ir.actions.act_window",
            "views": [[False, "form"]],
            "res_model": "account.report.send",
            "target": "new",
            "context": {
                "default_mail_template_id": template.id if template else False,
                "default_report_options": options,
            },
        }
