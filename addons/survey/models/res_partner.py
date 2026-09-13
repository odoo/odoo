from typing import Any

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    certifications_count = fields.Integer(compute="_compute_certifications_count")
    certifications_company_count = fields.Integer(
        string="Company Certifications Count",
        compute="_compute_certifications_company_count",
    )

    def _get_domain_certification(self, partner_ids: list[int] | None = None) -> list:
        return [
            ("partner_id", "in", self.ids if partner_ids is None else partner_ids),
            ("scoring_success", "=", True),
            ("state", "=", "done"),
            ("test_entry", "=", False),
        ]

    def _compute_certifications_count(self) -> None:
        read_group_res = (
            self.env["survey.user_input"]
            .sudo()
            ._read_group(
                self._get_domain_certification(),
                ["partner_id"],
                ["__count"],
            )
        )
        data = {partner.id: count for partner, count in read_group_res}
        for partner in self:
            partner.certifications_count = data.get(partner.id, 0)

    @api.depends("is_company", "child_ids.certifications_count")
    def _compute_certifications_company_count(self) -> None:
        for partner in self:
            partner.certifications_company_count = sum(
                child.certifications_count for child in partner.child_ids
            )

    def action_view_certifications(self) -> dict[str, Any]:
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "survey.res_partner_action_certifications"
        )
        action["view_mode"] = "list"
        action["domain"] = self._get_domain_certification(
            partner_ids=(self | self.child_ids).ids
        )
        return action
