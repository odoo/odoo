from odoo import _, api, fields, models
from odoo.exceptions import AccessError

from ..tools import debug_log as dbg


class DigestDigest(models.Model):
    _inherit = "digest.digest"

    kpi_pos_total = fields.Boolean(string="POS Sales")
    kpi_pos_total_value = fields.Monetary(compute="_compute_kpi_pos_total_value")

    @api.depends_context("uid")
    def _compute_kpi_pos_total_value(self):
        if not self.env.user.has_group("point_of_sale.group_pos_user"):
            raise AccessError(
                _("Do not have access, skip this data for user's digest email")
            )

        with dbg.timer(self.env, "digest kpi_pos_total_value for %s", dbg.rec(self)):
            self._update_company_based_kpi(
                "pos.order",
                "kpi_pos_total_value",
                date_field="date_order",
                additional_domain=[
                    ("state", "not in", ["draft", "cancel"]),
                    ("account_move", "=", False),
                ],
                sum_field="amount_total",
            )

    def _get_kpi_actions(self, company, user):
        res = super()._get_kpi_actions(company, user)
        res["kpi_pos_total"] = (
            "point_of_sale.action_pos_sale_graph?menu_id=%s"
            % self.env.ref("point_of_sale.menu_point_root").id
        )
        return res
