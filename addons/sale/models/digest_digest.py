from odoo import _, fields, models
from odoo.exceptions import AccessError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class DigestDigest(models.Model):
    _inherit = "digest.digest"

    kpi_all_sale_total = fields.Boolean(string="All Sales")
    kpi_all_sale_total_value = fields.Monetary(
        compute="_compute_kpi_all_sale_total_value"
    )

    def _compute_kpi_all_sale_total_value(self):
        if not self.env.user.has_group("sale.group_sale_salesman_all_leads"):
            _debug.logic("digest_kpi_denied", kpi="all_sale_total", digests=self)
            raise AccessError(
                _("Do not have access, skip this data for user's digest email")
            )

        self._update_company_based_kpi(
            "sale.report",
            "kpi_all_sale_total_value",
            date_field="date_order",
            additional_domain=[("state", "not in", ["draft", "cancel"])],
            sum_field="price_total",
        )

    def _get_kpi_actions(self, company, user):
        res = super()._get_kpi_actions(company, user)
        res["kpi_all_sale_total"] = (
            "sale.action_sale_report_all_channels_sales?menu_id=%s"
            % self.env.ref("sale.sale_menu_root").id
        )
        return res
