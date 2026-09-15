from ast import literal_eval
from collections import defaultdict

from odoo import _, api, fields, models


class EventLeadRule(models.Model):
    _name = "event.lead.rule"
    _description = "Event Lead Rules"

    name = fields.Char(
        string="Rule Name",
        translate=True,
        required=True,
    )
    active = fields.Boolean(default=True)
    lead_ids = fields.One2many(
        comodel_name="crm.lead",
        inverse_name="event_lead_rule_id",
        string="Created Leads",
        groups="sale.group_sale_salesman",
    )
    lead_creation_basis = fields.Selection(
        selection=[("attendee", "Per Attendee"), ("order", "Per Order")],
        string="Create",
        default="attendee",
        required=True,
        help="Per Attendee: A Lead is created for each Attendee (B2C).\n"
        "Per Order: A single Lead is created per Ticket Batch/Sale Order (B2B)",
    )
    lead_creation_trigger = fields.Selection(
        selection=[
            ("create", "Attendees are created"),
            ("confirm", "Attendees are registered"),
            ("done", "Attendees attended"),
        ],
        string="When",
        default="create",
        required=True,
        help="Creation: at attendee creation;\n"
        "Registered: at attendee registration, manually or automatically;\n"
        "Attended: when attendance is confirmed and registration set to done;",
    )
    event_type_ids = fields.Many2many(
        comodel_name="event.type",
        string="Event Templates",
        help="Filter the attendees to include those of this specific event category. If not set, no event category restriction will be applied.",
    )
    event_id = fields.Many2one(
        comodel_name="event.event",
        domain="[('company_id', 'in', [company_id or current_company_id, False])]",
        help="Filter the attendees to include those of this specific event. If not set, no event restriction will be applied.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        help="Restrict the trigger of this rule to events belonging to a specific company.\nIf not set, no company restriction will be applied.",
    )
    event_registration_filter = fields.Text(
        string="Registrations Domain",
        help="Filter the attendees that will or not generate leads.",
    )
    lead_type = fields.Selection(
        selection=[("lead", "Lead"), ("opportunity", "Opportunity")],
        default=lambda self: (
            "lead" if self.env.user.has_group("crm.group_use_lead") else "opportunity"
        ),
        required=True,
        help="Default lead type when this rule is applied.",
    )
    lead_sales_team_id = fields.Many2one(
        comodel_name="team.team",
        string="Sales Team",
        domain=[("use_sale", "=", True)],
        ondelete="set null",
        help="Automatically assign the created leads to this Sales Team.",
    )
    lead_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Salesperson",
        help="Automatically assign the created leads to this Salesperson.",
    )
    lead_tag_ids = fields.Many2many(
        comodel_name="crm.tag",
        string="Tags",
        help="Automatically add these tags to the created leads.",
    )

    @api.onchange("lead_sales_team_id")
    def _onchange_lead_sales_team_id(self):
        if self.lead_sales_team_id and self.lead_sales_team_id.user_id:
            self.lead_user_id = self.lead_sales_team_id.user_id

    def _run_on_registrations(self, registrations):
        if not self:
            return self.env["crm.lead"]

        registrations = registrations.sorted("id")

        existing_leads = (
            self.env["crm.lead"]
            .with_context(active_test=False)
            .search(
                [
                    ("registration_ids", "in", registrations.ids),
                    ("event_lead_rule_id", "in", self.ids),
                ]
            )
        )
        rule_to_existing_regs = defaultdict(lambda: self.env["event.registration"])
        for lead in existing_leads:
            rule_to_existing_regs[lead.event_lead_rule_id] += lead.registration_ids

        new_registrations = self.env["event.registration"]
        rule_to_new_regs = {}
        for rule in self:
            new_for_rule = registrations.filtered(
                lambda reg, rule=rule: reg not in rule_to_existing_regs[rule]
            )
            rule_registrations = rule._filter_registrations(new_for_rule)
            new_registrations |= rule_registrations
            rule_to_new_regs[rule] = rule_registrations
        new_registrations.sorted("id")

        order_based_rules = self.filtered(
            lambda rule: rule.lead_creation_basis == "order"
        )
        rule_group_info = new_registrations._get_lead_grouping(
            order_based_rules, rule_to_new_regs
        )

        lead_vals_list = []
        for rule in self:
            if rule.lead_creation_basis == "attendee":
                matching_registrations = rule_to_new_regs[rule].sorted("id")
                lead_vals_list.extend(
                    registration._prepare_lead_vals(rule)
                    for registration in matching_registrations
                )
            else:
                for toupdate_leads, _group_key, group_registrations in rule_group_info[
                    rule
                ]:
                    if toupdate_leads:
                        additionnal_description = (
                            group_registrations._get_lead_description(
                                _("New registrations"), line_counter=True
                            )
                        )
                        for lead in toupdate_leads:
                            lead.write(
                                {
                                    "description": "%s<br/>%s"
                                    % (lead.description, additionnal_description),
                                    "registration_ids": [
                                        (4, reg.id) for reg in group_registrations
                                    ],
                                }
                            )
                    elif group_registrations:
                        lead_vals_list.append(
                            group_registrations._prepare_lead_vals(rule)
                        )

        return self.env["crm.lead"].create(lead_vals_list)

    def action_execute_rule(self):
        events = self.event_id or self.env["event.event"].search(
            [("is_finished", "!=", True)]
        )
        return events.action_generate_leads(event_lead_rules=self)

    def _filter_registrations(self, registrations):
        self.check_singleton()
        if self.event_registration_filter and self.event_registration_filter != "[]":
            registrations = registrations.filtered_domain(
                literal_eval(self.event_registration_filter)
            )

        def company_ok(registration):
            return (
                registration.company_id == self.company_id if self.company_id else True
            )

        def event_or_event_type_ok(registration):
            return (
                registration.event_id == self.event_id
                or registration.event_id.event_type_id in self.event_type_ids
                if (self.event_id or self.event_type_ids)
                else True
            )

        return registrations.filtered(
            lambda r: company_ok(r) and event_or_event_type_ok(r)
        )
