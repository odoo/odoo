import logging

from odoo import _, api, fields, models, release
from odoo.exceptions import UserError
from odoo.tools import is_html_empty

from odoo.addons.iap.tools import iap_tools

_logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = "https://iap-services.odoo.com"

MAX_LEAD = 200

MAX_CONTACT = 5

CREDIT_PER_COMPANY = 1
CREDIT_PER_CONTACT = 1


class CrmIapLeadMiningRequest(models.Model):
    _name = "crm.iap.lead.mining.request"
    _description = "CRM Lead Mining Request"

    def _default_lead_type(self):
        if self.env.user.has_group("crm.group_use_lead"):
            return "lead"
        else:
            return "opportunity"

    def _default_country_ids(self):
        return self.env.user.company_id.country_id

    name = fields.Char(
        string="Request Number",
        default=lambda self: _("New"),
        copy=False,
        readonly=True,
        required=True,
    )
    state = fields.Selection(
        selection=[("draft", "Draft"), ("error", "Error"), ("done", "Done")],
        string="Status",
        default="draft",
        required=True,
    )

    lead_number = fields.Integer(
        string="Number of Leads",
        default=3,
        required=True,
    )
    search_type = fields.Selection(
        selection=[
            ("companies", "Companies"),
            ("people", "Companies and their Contacts"),
        ],
        string="Target",
        default="companies",
        required=True,
    )
    error_type = fields.Selection(
        selection=[
            ("credits", "Insufficient Credits"),
            ("no_result", "No Result"),
        ],
        copy=False,
        readonly=True,
    )

    lead_type = fields.Selection(
        selection=[("lead", "Leads"), ("opportunity", "Opportunities")],
        string="Type",
        default=_default_lead_type,
        required=True,
    )
    team_id = fields.Many2one(
        comodel_name="team.team",
        string="Sales Team",
        compute="_compute_team_id",
        store=True,
        readonly=False,
        domain="[('use_sale', '=', True), ('use_opportunities', '=', True)]",
        ondelete="set null",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Salesperson",
        default=lambda self: self.env.user,
    )
    tag_ids = fields.Many2many(
        comodel_name="crm.tag",
        string="Tags",
    )
    lead_ids = fields.One2many(
        comodel_name="crm.lead",
        inverse_name="lead_mining_request_id",
        string="Generated Lead / Opportunity",
    )
    lead_count = fields.Integer(
        string="Number of Generated Leads",
        compute="_compute_lead_count",
    )

    filter_on_size = fields.Boolean(
        string="Filter on Size",
        default=False,
    )
    company_size_min = fields.Integer(
        string="Size",
        default=1,
    )
    company_size_max = fields.Integer(default=1000)
    country_ids = fields.Many2many(
        comodel_name="res.country",
        string="Countries",
        default=_default_country_ids,
    )
    state_ids = fields.Many2many(
        comodel_name="res.country.state",
        string="States",
    )
    available_state_ids = fields.One2many(
        comodel_name="res.country.state",
        compute="_compute_available_state_ids",
    )
    industry_ids = fields.Many2many(
        comodel_name="crm.iap.lead.industry",
        string="Industries",
    )

    contact_number = fields.Integer(
        string="Number of Contacts",
        default=10,
    )
    contact_filter_type = fields.Selection(
        selection=[("role", "Role"), ("seniority", "Seniority")],
        string="Filter on",
        default="role",
    )
    preferred_role_id = fields.Many2one(comodel_name="crm.iap.lead.role")
    role_ids = fields.Many2many(
        comodel_name="crm.iap.lead.role",
        string="Other Roles",
    )
    seniority_id = fields.Many2one(comodel_name="crm.iap.lead.seniority")

    lead_credits = fields.Char(
        compute="_compute_tooltip",
        readonly=True,
    )
    lead_contacts_credits = fields.Char(
        compute="_compute_tooltip",
        readonly=True,
    )
    lead_total_credits = fields.Char(
        compute="_compute_tooltip",
        readonly=True,
    )

    @api.onchange("lead_number", "contact_number")
    def _compute_tooltip(self):
        for record in self:
            company_credits = CREDIT_PER_COMPANY * record.lead_number
            contact_credits = CREDIT_PER_CONTACT * record.contact_number
            total_contact_credits = contact_credits * record.lead_number
            record.lead_contacts_credits = _(
                "Up to %(credit_count)d additional credits will be consumed to identify %(contact_count)d contacts per company.",
                credit_count=contact_credits * company_credits,
                contact_count=record.contact_number,
            )
            record.lead_credits = _(
                "%(credit_count)d credits will be consumed to find %(company_count)d companies.",
                credit_count=company_credits,
                company_count=record.lead_number,
            )
            record.lead_total_credits = _(
                "This makes a total of %d credits for this request.",
                total_contact_credits + company_credits,
            )

    @api.depends("lead_ids.lead_mining_request_id")
    def _compute_lead_count(self):
        leads_data = self.env["crm.lead"]._read_group(
            [("lead_mining_request_id", "in", self.ids)],
            ["lead_mining_request_id"],
            ["__count"],
        )
        mapped_data = {
            lead_mining_request.id: count for lead_mining_request, count in leads_data
        }
        for request in self:
            request.lead_count = mapped_data.get(request.id, 0)

    @api.depends("user_id", "lead_type")
    def _compute_team_id(self):
        for mining in self:
            if not mining.user_id:
                continue
            user = mining.user_id
            if (
                mining.team_id
                and user in mining.team_id.member_ids | mining.team_id.user_id
            ):
                continue
            team_domain = (
                [("use_leads", "=", True)]
                if mining.lead_type == "lead"
                else [("use_opportunities", "=", True)]
            )
            team = self.env["team.team"]._get_default_team(
                "sale", user_id=user.id, domain=team_domain
            )
            mining.team_id = team.id

    @api.depends("country_ids")
    def _compute_available_state_ids(self):
        for lead_mining_request in self:
            countries = lead_mining_request.country_ids.filtered(
                lambda country: (
                    country.code in iap_tools._STATES_FILTER_COUNTRIES_WHITELIST
                )
            )
            lead_mining_request.available_state_ids = self.env[  # noqa: E8507 - one query per request, on its own countries
                "res.country.state"
            ].search([("country_id", "in", countries.ids)])

    @api.onchange("available_state_ids")
    def _onchange_available_state_ids(self):
        self.state_ids -= self.state_ids.filtered(
            lambda state: (
                (state._origin.id or state.id) not in self.available_state_ids.ids
            )
        )

    @api.onchange("lead_number")
    def _onchange_lead_number(self):
        if self.lead_number <= 0:
            self.lead_number = 1
        elif self.lead_number > MAX_LEAD:
            self.lead_number = MAX_LEAD

    @api.onchange("contact_number")
    def _onchange_contact_number(self):
        if self.contact_number <= 0:
            self.contact_number = 1
        elif self.contact_number > MAX_CONTACT:
            self.contact_number = MAX_CONTACT

    @api.onchange("country_ids")
    def _onchange_country_ids(self):
        self.state_ids = []

    @api.onchange("company_size_min")
    def _onchange_company_size_min(self):
        if self.company_size_min <= 0:
            self.company_size_min = 1
        elif self.company_size_min > self.company_size_max:
            self.company_size_min = self.company_size_max

    @api.onchange("company_size_max")
    def _onchange_company_size_max(self):
        self.company_size_max = max(self.company_size_max, self.company_size_min)

    @api.model
    def get_empty_list_help(self, help_message):
        if not is_html_empty(help_message):
            return help_message

        help_title = _("Create a Lead Mining Request")
        sub_title = _("Generate new leads based on their country, industry, size, etc.")
        return super().get_empty_list_help(
            f'<p class="o_view_nocontent_smiling_face">{help_title}</p><p class="oe_view_nocontent_alias">{sub_title}</p>'
        )

    def _prepare_iap_payload(self):
        self.check_singleton()
        payload = {
            "lead_number": self.lead_number,
            "search_type": self.search_type,
            "countries": [
                {
                    "code": country.code,
                    "states": self.state_ids.filtered(
                        lambda state: state in country.state_ids
                    ).mapped("code"),
                }
                for country in self.country_ids
            ],
        }

        if self.filter_on_size:
            payload.update(
                {
                    "company_size_min": self.company_size_min,
                    "company_size_max": self.company_size_max,
                }
            )
        if self.industry_ids:
            all_industry_ids = [
                reveal_id.strip()
                for reveal_ids in self.mapped("industry_ids.reveal_ids")
                for reveal_id in reveal_ids.split(",")
            ]
            payload["industry_ids"] = all_industry_ids
        if self.search_type == "people":
            payload.update(
                {
                    "contact_number": self.contact_number,
                    "contact_filter_type": self.contact_filter_type,
                }
            )
            if self.contact_filter_type == "role":
                payload.update(
                    {
                        "preferred_role": self.preferred_role_id.reveal_id,
                        "other_roles": self.role_ids.mapped("reveal_id"),
                    }
                )
            elif self.contact_filter_type == "seniority":
                payload["seniority"] = self.seniority_id.reveal_id
        return payload

    def _perform_request(self):
        self.error_type = False
        server_payload = self._prepare_iap_payload()
        reveal_account = self.env["iap.account"].get("reveal")
        dbuuid = self.env["ir.config_parameter"].sudo().get_param("database.uuid")
        reveal_ids = [
            lead["reveal_id"]
            for lead in self.env["crm.lead"].search_read(
                [("reveal_id", "!=", False)], ["reveal_id"]
            )
        ]
        params = {
            "account_token": reveal_account.sudo().account_token,
            "db_uuid": dbuuid,
            "query": server_payload,
            "db_version": release.version,
            "db_lang": self.env.lang,
            "country_code": self.env.company.country_id.code,
            "reveal_ids": reveal_ids,
        }
        try:
            response = self._iap_contact_mining(params, timeout=300)
            if not response.get("data"):
                self.error_type = "no_result"
                return False

            return response["data"]
        except iap_tools.InsufficientCreditError:
            self.error_type = "credits"
            self.state = "error"
            return False
        except Exception as e:
            raise UserError(_("Your request could not be executed: %s", e))

    def _iap_contact_mining(self, params, timeout=300):
        endpoint = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("reveal.endpoint", DEFAULT_ENDPOINT)
            + "/api/dnb/1/search_by_criteria"
        )
        return iap_tools.iap_jsonrpc(
            endpoint, params=params, timeout=timeout, env=self.env
        )

    def _create_leads_from_response(self, result):
        self.check_singleton()
        lead_vals_list = []
        messages_to_post = {}
        for data in result:
            country = self.env["res.country"].search(  # noqa: E8507 - one lookup per row of the mining response
                [("code", "=", data["country_code"])]
            )
            lead_vals_list.append(self._lead_vals_from_response(data))

            template_values = data
            template_values.update(
                {
                    "flavor_text": _("Opportunity created by Odoo Lead Generation"),
                    "people_data": data.get("people_data"),
                    "country": country.name,
                    "zip_code": data.get("zip"),
                    "country_id": country.id,
                }
            )
            messages_to_post[data["duns"]] = template_values
        leads = self.env["crm.lead"].create(lead_vals_list)
        for lead in leads:
            if messages_to_post.get(lead.reveal_id):
                lead.message_post_with_source(
                    "iap_mail.enrich_company",
                    render_values=messages_to_post[lead.reveal_id],
                    subtype_xmlid="mail.mt_note",
                )

    @api.model
    def _lead_vals_from_response(self, data):
        self.check_singleton()
        company_data = data
        people_data = []
        lead_vals = self.env["crm.iap.lead.helpers"].lead_vals_from_response(
            self.lead_type,
            self.team_id.id,
            self.tag_ids.ids,
            self.user_id.id,
            company_data,
            people_data,
        )
        lead_vals["lead_mining_request_id"] = self.id
        return lead_vals

    def action_draft(self):
        self.check_singleton()
        self.name = _("New")
        self.state = "draft"

    def action_submit(self):
        self.check_singleton()
        if self.name == _("New"):
            self.name = self.env["ir.sequence"].next_by_code(
                "crm.iap.lead.mining.request"
            ) or _("New")
        results = self._perform_request()

        if results:
            self._create_leads_from_response(results)
            self.state = "done"
            if self.lead_type == "lead":
                return self.action_get_lead_action()
            elif self.lead_type == "opportunity":
                return self.action_get_opportunity_action()
        elif self.env.context.get("is_modal"):
            return {
                "name": _("Generate Leads"),
                "res_model": "crm.iap.lead.mining.request",
                "views": [[False, "form"]],
                "target": "new",
                "type": "ir.actions.act_window",
                "res_id": self.id,
                "context": dict(self.env.context, edit=True),
            }
        else:
            return False

    def action_get_lead_action(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "crm.crm_lead_all_leads"
        )
        action["domain"] = [("id", "in", self.lead_ids.ids), ("type", "=", "lead")]
        return action

    def action_get_opportunity_action(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "crm.crm_lead_opportunities"
        )
        action["domain"] = [
            ("id", "in", self.lead_ids.ids),
            ("type", "=", "opportunity"),
        ]
        return action

    def action_buy_credits(self):
        return {
            "type": "ir.actions.act_url",
            "url": self.env["iap.account"].get_credits_url(service_name="reveal"),
        }
