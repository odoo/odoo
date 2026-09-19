from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import html2plaintext

_debug = DebugLog(__name__)


class ReportConfig(models.Model):
    _name = "report.config"
    _description = "How a company's printed documents look"
    _inherit = ["mixin.company.config"]

    report_header = fields.Html(
        string="Company Tagline",
        translate=True,
        help="Company tagline, which is included in a printed document's header or footer (depending on the selected layout).",
    )
    report_footer = fields.Html(
        translate=True,
        help="Footer text displayed at the bottom of all reports.",
    )
    company_details = fields.Html(
        translate=True,
        help="Header text displayed at the top of all reports.",
    )
    is_company_details_empty = fields.Boolean(
        compute="_compute_is_company_details_empty"
    )
    paperformat_id = fields.Many2one(
        comodel_name="report.paperformat",
        string="Paper format",
        default=lambda self: self.env.ref(
            "base.paperformat_euro",
            raise_if_not_found=False,
        ),
    )

    def init(self) -> None:
        paperformat_euro = self.env.ref("base.paperformat_euro", False)
        if paperformat_euro:
            without = self.search([("paperformat_id", "=", False)])
            if without:
                _debug.lifecycle("init_paperformat_set", configs=without.ids)
                without.write({"paperformat_id": paperformat_euro.id})
        super().init()

    @api.depends("company_details")
    def _compute_is_company_details_empty(self) -> None:
        for record in self:
            record.is_company_details_empty = not html2plaintext(
                record.company_details or ""
            )
