from odoo import api, fields, models


class CrmLead2opportunityPartnerMass(models.TransientModel):
    _name = "crm.lead2opportunity.partner.mass"
    _description = "Convert Lead to Opportunity (in mass)"
    _inherit = ["crm.lead2opportunity.partner"]

    lead_id = fields.Many2one(required=False)
    lead_tomerge_ids = fields.Many2many(
        comodel_name="crm.lead",
        relation="crm_convert_lead_mass_lead_rel",
        string="Active Leads",
        default=lambda self: self.env.context.get("active_ids", []),
        context={"active_test": False},
    )
    user_ids = fields.Many2many(
        comodel_name="res.users",
        string="Salespersons",
    )
    deduplicate = fields.Boolean(
        string="Apply deduplication",
        default=True,
        help="Merge with existing leads/opportunities of each partner",
    )
    action = fields.Selection(
        selection_add=[
            ("each_exist_or_create", "Use existing partner or create"),
        ],
        string="Related Customer",
        ondelete={
            "each_exist_or_create": lambda recs: recs.write({"action": "exist"}),
        },
    )
    force_assignment = fields.Boolean(default=False)

    @api.depends("duplicated_lead_ids")
    def _compute_name(self):
        for convert in self:
            convert.name = "convert"

    @api.depends("lead_tomerge_ids")
    def _compute_action(self):
        for convert in self:
            convert.action = "each_exist_or_create"

    @api.depends("lead_tomerge_ids")
    def _compute_partner_id(self):
        for convert in self:
            convert.partner_id = False

    def _compute_commercial_partner_id(self):
        self.commercial_partner_id = False

    @api.depends("user_ids")
    def _compute_team_id(self):
        Team = self.env["team.team"]
        for convert in self:
            if not convert.user_id and not convert.user_ids and convert.team_id:
                continue
            user = convert.user_id or convert.user_ids[:1] or self.env.user
            convert.team_id = Team._get_team_for_user(user, convert.team_id).id

    @api.depends("lead_tomerge_ids")
    def _compute_duplicated_lead_ids(self):
        for convert in self:
            duplicates_by_lead = self.env["crm.lead"]._get_lead_duplicates_by_lead(
                convert.lead_tomerge_ids, with_partner=True, include_lost=False
            )
            convert.duplicated_lead_ids = [
                lead.id
                for lead, duplicates in duplicates_by_lead.items()
                if len(duplicates) > 1
            ]

    def _convert_and_allocate(self, leads, user_ids, team_id=False):
        self.check_singleton()
        salesmen_ids = []
        if self.user_ids:
            salesmen_ids = self.user_ids.ids
        return super()._convert_and_allocate(leads, salesmen_ids, team_id=team_id)

    def action_mass_convert(self):
        self.check_singleton()
        if self.name == "convert" and self.deduplicate:
            active_ids = self.env.context.get("active_ids", [])
            merged_lead_ids = set()
            remaining_lead_ids = set()
            for lead in self.lead_tomerge_ids:
                if lead.id not in merged_lead_ids:
                    duplicated_leads = self.env["crm.lead"]._get_lead_duplicates(
                        partner=lead.partner_id,
                        email=lead.partner_id.email or lead.email_from,
                        include_lost=False,
                    )
                    if len(duplicated_leads) > 1:
                        lead = duplicated_leads.merge_opportunity()
                        merged_lead_ids.update(duplicated_leads.ids)
                        remaining_lead_ids.add(lead.id)
            final_ids = [
                lead_id for lead_id in active_ids if lead_id not in merged_lead_ids
            ]
            final_ids += [
                lead_id for lead_id in remaining_lead_ids if lead_id not in final_ids
            ]

            self = self.with_context(active_ids=final_ids)
        return self.action_apply()

    def _convert_handle_partner(self, lead, action, partner_id):
        if self.action == "each_exist_or_create":
            partner_id = lead._find_matching_partner().id
            action = "create"
        return super()._convert_handle_partner(lead, action, partner_id)
