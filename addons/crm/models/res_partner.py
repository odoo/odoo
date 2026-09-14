from odoo import _, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    opportunity_ids = fields.One2many(
        comodel_name="crm.lead",
        inverse_name="partner_id",
        string="Opportunities",
        domain=[("type", "=", "opportunity")],
    )
    opportunity_count = fields.Integer(
        compute="_compute_opportunity_count",
        groups="sale.group_sale_salesman",
    )

    def _get_children_partners_for_hierarchy(self):
        return self.with_context(active_test=False).search_fetch(
            [("id", "child_of", self.ids)],
            ["parent_id"],
        )

    def _get_domain_contact_opportunities(self):
        return [("partner_id", "in", self._get_children_partners_for_hierarchy().ids)]

    def _compute_opportunity_count(self):
        self.opportunity_count = 0
        if not self.env.user.has_group("sale.group_sale_salesman"):
            return
        opportunity_data = (
            self.env["crm.lead"]
            .with_context(active_test=False)
            ._read_group(
                domain=self._get_domain_contact_opportunities(),
                groupby=["partner_id"],
                aggregates=["__count"],
            )
        )
        current_pids = set(self._ids)
        for partner, count in opportunity_data:
            while partner:
                if partner.id in current_pids:
                    partner.opportunity_count += count
                partner = partner.parent_id

    def _get_application_statistics(self):
        data_list = super()._get_application_statistics()
        if not self.env.user.has_group("sale.group_sale_salesman"):
            return data_list
        for partner in self.filtered("opportunity_count"):
            data_list[partner.id].append(
                {
                    "iconClass": "fa-solid fa-star",
                    "value": partner.opportunity_count,
                    "label": _("Opportunities"),
                    "tagClass": "o_tag_color_8",
                }
            )
        return data_list

    def action_view_opportunity(self):
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "crm.crm_lead_opportunities"
        )
        action["context"] = {
            "search_default_filter_won": 1,
            "search_default_filter_ongoing": 1,
            "search_default_filter_lost": 1,
            "active_test": False,
        }
        action["views"] = sorted(action["views"], key=lambda view: view[1] != "list")
        action["domain"] = self._get_domain_contact_opportunities()
        return action
