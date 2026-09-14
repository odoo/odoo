from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class CrmLead2opportunityPartner(models.TransientModel):
    _name = "crm.lead2opportunity.partner"
    _description = "Convert Lead to Opportunity (not in mass)"

    @api.model
    def default_get(self, fields):
        result = super().default_get(fields)

        if (
            "lead_id" in fields
            and not result.get("lead_id")
            and self.env.context.get("active_id")
        ):
            result["lead_id"] = self.env.context.get("active_id")

        if result.get("lead_id"):
            if self.env["crm.lead"].browse(result["lead_id"]).probability == 100:
                raise UserError(
                    _("Closed/Dead leads cannot be converted into opportunities.")
                )

        return result

    name = fields.Selection(
        selection=[
            ("convert", "Convert to opportunity"),
            ("merge", "Merge with existing opportunities"),
        ],
        string="Conversion Action",
        compute="_compute_name",
        compute_sudo=False,
        store=True,
        readonly=False,
    )
    action = fields.Selection(
        selection=[
            ("create", "Create a new customer"),
            ("exist", "Link to an existing customer"),
        ],
        string="Related Customer",
        compute="_compute_action",
        precompute=True,
        compute_sudo=False,
        store=True,
        readonly=False,
        required=True,
    )
    lead_id = fields.Many2one(
        comodel_name="crm.lead",
        string="Associated Lead",
        required=True,
    )
    lead_partner_name = fields.Char(
        related="lead_id.partner_name",
        help=False,
    )
    lead_contact_name = fields.Char(
        related="lead_id.contact_name",
        help=False,
    )
    duplicated_lead_ids = fields.Many2many(
        comodel_name="crm.lead",
        string="Opportunities",
        compute="_compute_duplicated_lead_ids",
        compute_sudo=False,
        store=True,
        readonly=False,
        context={"active_test": False},
    )
    commercial_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Company",
        compute="_compute_commercial_partner_id",
        compute_sudo=False,
        store=True,
        readonly=False,
        domain=[("is_company", "=", True)],
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer",
        compute="_compute_partner_id",
        compute_sudo=False,
        store=True,
        readonly=False,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Salesperson",
        compute="_compute_user_id",
        compute_sudo=False,
        store=True,
        readonly=False,
    )
    team_id = fields.Many2one(
        comodel_name="team.team",
        string="Sales Team",
        compute="_compute_team_id",
        compute_sudo=False,
        store=True,
        readonly=False,
        domain=[("use_sale", "=", True)],
    )
    force_assignment = fields.Boolean(
        string="Force assignment",
        default=True,
        help="If checked, forces salesman to be updated on updated opportunities even if already set.",
    )

    @api.depends("duplicated_lead_ids")
    def _compute_name(self):
        for convert in self:
            if not convert.name:
                convert.name = (
                    "merge"
                    if convert.duplicated_lead_ids
                    and len(convert.duplicated_lead_ids) >= 2
                    else "convert"
                )

    @api.depends("lead_id")
    def _compute_action(self):
        for convert in self:
            partner = convert.lead_id and convert.lead_id._find_matching_partner()
            convert.action = "exist" if partner else "create"

    @api.depends("lead_id", "partner_id")
    def _compute_duplicated_lead_ids(self):
        for convert in self:
            if not convert.lead_id:
                convert.duplicated_lead_ids = False
                continue
            convert.duplicated_lead_ids = (
                self.env["crm.lead"]
                ._get_lead_duplicates(
                    convert.partner_id,
                    convert.lead_id.partner_id.email or convert.lead_id.email_from,
                    include_lost=True,
                )
                .ids
            )

    @api.depends("partner_id")
    def _compute_commercial_partner_id(self):
        for convert in self.filtered("partner_id"):
            if (
                not convert.commercial_partner_id
                or (
                    convert.commercial_partner_id
                    and not convert.commercial_partner_id.filtered_domain(
                        [("id", "parent_of", convert.commercial_partner_id)]
                    )
                )
            ) and convert.partner_id.parent_id:
                convert.commercial_partner_id = convert.partner_id.parent_id

    @api.depends("action", "lead_id")
    def _compute_partner_id(self):
        for convert in self:
            if convert.action == "exist":
                convert.partner_id = convert.lead_id._find_matching_partner()
            else:
                convert.partner_id = False

    @api.depends("lead_id")
    def _compute_user_id(self):
        for convert in self:
            convert.user_id = convert.lead_id.user_id or False

    @api.depends("user_id")
    def _compute_team_id(self):
        Team = self.env["team.team"]
        for convert in self:
            if not convert.user_id:
                continue
            convert.team_id = Team._get_team_for_user(
                convert.user_id, convert.team_id
            ).id

    def action_apply(self):
        if self.name == "merge":
            result_opportunity = self._action_merge()
        else:
            result_opportunity = self._action_convert()

        return result_opportunity.redirect_lead_opportunity_view()

    def _action_merge(self):
        to_merge = self.duplicated_lead_ids | self.lead_id
        result_opportunity = to_merge.merge_opportunity(auto_unlink=False)
        result_opportunity.action_unarchive()

        if result_opportunity.type == "lead":
            self._convert_and_allocate(
                result_opportunity, [self.user_id.id], team_id=self.team_id.id
            )
        elif not result_opportunity.user_id or self.force_assignment:
            result_opportunity.write(
                {
                    "user_id": self.user_id.id,
                    "team_id": self.team_id.id,
                }
            )
        if self.lead_id != result_opportunity:
            self.write({"lead_id": result_opportunity})
        merged_away = to_merge - result_opportunity
        merged_away.check_access("write")
        merged_away.sudo().unlink()
        return result_opportunity

    def _action_convert(self):
        result_opportunities = self.env["crm.lead"].browse(
            self.env.context.get("active_ids", [])
        )
        self._convert_and_allocate(
            result_opportunities, [self.user_id.id], team_id=self.team_id.id
        )
        return result_opportunities[0]

    def _convert_and_allocate(self, leads, user_ids, team_id=False):
        self.check_singleton()

        for lead in leads:
            if lead.active:
                self._convert_handle_partner(
                    lead, self.action, self.partner_id.id or lead.partner_id.id
                )

            lead.convert_opportunity(lead.partner_id, user_ids=False, team_id=False)

        leads_to_allocate = leads
        if not self.force_assignment:
            leads_to_allocate = leads_to_allocate.filtered(
                lambda lead: not lead.user_id
            )

        if user_ids:
            leads_to_allocate._handle_salesmen_assignment(user_ids, team_id=team_id)

    def _convert_handle_partner(self, lead, action, partner_id):
        lead.with_context(default_user_id=self.user_id.id)._handle_partner_assignment(
            force_partner_id=partner_id,
            create_missing=action == "create",
            with_parent=self.commercial_partner_id,
        )
