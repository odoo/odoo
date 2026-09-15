import datetime
import itertools
import logging
import re

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

from odoo.addons.crm.models import crm_stage
from odoo.addons.iap.tools import iap_tools

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

DEFAULT_ENDPOINT = "https://iap-services.odoo.com"
DEFAULT_REVEAL_BATCH_LIMIT = 25
DEFAULT_REVEAL_MONTH_VALID = 6


class CrmRevealRule(models.Model):
    _name = "crm.reveal.rule"
    _description = "CRM Lead Generation Rules"
    _order = "sequence"

    name = fields.Char(
        string="Rule Name",
        required=True,
    )
    active = fields.Boolean(default=True)

    country_ids = fields.Many2many(
        comodel_name="res.country",
        string="Countries",
        help="Only visitors of following countries will be converted into leads/opportunities (using GeoIP).",
    )
    website_id = fields.Many2one(
        comodel_name="website",
        help="Restrict Lead generation to this website.",
    )
    state_ids = fields.Many2many(
        comodel_name="res.country.state",
        string="States",
        help="Only visitors of following states will be converted into leads/opportunities.",
    )
    regex_url = fields.Char(
        string="URL Expression",
        help="Regex to track website pages. Leave empty to track the entire website, or / to target the homepage. Example: /page* to track all the pages which begin with /page",
    )
    sequence = fields.Integer(
        help="Used to order the rules with same URL and countries. "
        "Rules with a lower sequence number will be processed first."
    )

    industry_tag_ids = fields.Many2many(
        comodel_name="crm.iap.lead.industry",
        string="Industries",
        help="Leave empty to always match. Odoo will not create lead if no match",
    )
    filter_on_size = fields.Boolean(
        string="Filter on Size",
        default=True,
        help="Filter companies based on their size.",
    )
    company_size_min = fields.Integer(
        string="Company Size",
        default=0,
    )
    company_size_max = fields.Integer(default=1000)

    contact_filter_type = fields.Selection(
        selection=[("role", "Role"), ("seniority", "Seniority")],
        string="Filter On",
        default="role",
        required=True,
    )
    preferred_role_id = fields.Many2one(comodel_name="crm.iap.lead.role")
    other_role_ids = fields.Many2many(
        comodel_name="crm.iap.lead.role",
        string="Other Roles",
    )
    seniority_id = fields.Many2one(comodel_name="crm.iap.lead.seniority")
    extra_contacts = fields.Integer(
        string="Number of Contacts",
        default=1,
        help="This is the number of contacts to track if their role/seniority match your criteria. Their details will show up in the history thread of generated leads/opportunities. One credit is consumed per tracked contact.",
    )

    lead_for = fields.Selection(
        selection=[
            ("companies", "Companies"),
            ("people", "Companies and their Contacts"),
        ],
        string="Data Tracking",
        default="companies",
        required=True,
        help="Choose whether to track companies only or companies and their contacts",
    )
    lead_type = fields.Selection(
        selection=[("lead", "Lead"), ("opportunity", "Opportunity")],
        string="Type",
        default="opportunity",
        required=True,
    )
    suffix = fields.Char(
        help="This will be appended in name of generated lead so you can identify lead/opportunity is generated with this rule"
    )
    team_id = fields.Many2one(
        comodel_name="team.team",
        string="Sales Team",
        domain=[("use_sale", "=", True)],
        ondelete="set null",
    )
    tag_ids = fields.Many2many(
        comodel_name="crm.tag",
        string="Tags",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Salesperson",
    )
    priority = fields.Selection(selection=crm_stage.AVAILABLE_PRIORITIES)
    lead_ids = fields.One2many(
        comodel_name="crm.lead",
        inverse_name="reveal_rule_id",
        string="Generated Lead / Opportunity",
    )
    lead_count = fields.Integer(
        string="Number of Generated Leads",
        compute="_compute_lead_count",
    )
    opportunity_count = fields.Integer(
        string="Number of Generated Opportunity",
        compute="_compute_lead_count",
    )

    _limit_extra_contacts = models.Constraint(
        "check(extra_contacts >= 1 and extra_contacts <= 5)",
        "Maximum 5 contacts are allowed!",
    )

    def _compute_lead_count(self):
        leads = self.env["crm.lead"]._read_group(
            [("reveal_rule_id", "in", self.ids)],
            groupby=["reveal_rule_id", "type"],
            aggregates=["__count"],
        )
        mapping = {
            (reveal_rule.id, type_crm): count for reveal_rule, type_crm, count in leads
        }
        for rule in self:
            rule.lead_count = mapping.get((rule.id, "lead"), 0)
            rule.opportunity_count = mapping.get((rule.id, "opportunity"), 0)

    @api.constrains("regex_url")
    def _check_regex_url(self):
        try:
            if self.regex_url:
                re.compile(self.regex_url)
        except Exception as error:
            _debug.logic("reveal_rule_refused", reason="bad_regex", rule=self.id)
            raise ValidationError(_("Enter Valid Regex.")) from error

    @api.model_create_multi
    def create(self, vals_list):
        self.env.registry.clear_cache()
        return super().create(vals_list)

    def write(self, vals):
        fields_set = {"country_ids", "regex_url", "active"}
        if set(vals.keys()) & fields_set:
            self.env.registry.clear_cache()
        return super().write(vals)

    def unlink(self):
        self.env.registry.clear_cache()
        return super().unlink()

    def action_get_lead_tree_view(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "crm.crm_lead_all_leads"
        )
        action["domain"] = [("id", "in", self.lead_ids.ids), ("type", "=", "lead")]
        action["context"] = dict(self.env.context, create=False)
        return action

    def action_get_opportunity_tree_view(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "crm.crm_lead_opportunities"
        )
        action["domain"] = [
            ("id", "in", self.lead_ids.ids),
            ("type", "=", "opportunity"),
        ]
        action["context"] = dict(self.env.context, create=False)
        return action

    @api.model
    @tools.ormcache()
    def _get_active_rules(self):
        country_rules = {}
        rules_records = self.search([])
        rules = []
        for rule in rules_records:
            regex_url = rule["regex_url"]
            if not regex_url:
                regex_url = ".*"
            elif regex_url == "/":
                regex_url = ".*/$"
            countries = rule.country_ids.mapped("code")

            states = [(country_id.code, False) for country_id in rule.country_ids]
            if rule.state_ids:
                for state_id in rule.state_ids:
                    if (state_id.country_id.code, False) in states:
                        states.remove((state_id.country_id.code, False))
                    states += [(state_id.country_id.code, state_id.code)]

            rules.append(
                {
                    "id": rule.id,
                    "regex": regex_url,
                    "website_id": rule.website_id.id if rule.website_id else False,
                    "country_codes": countries,
                    "state_codes": states,
                }
            )
            for country in countries:
                country_rules = self._add_to_country(
                    country_rules, country, len(rules) - 1
                )
        return {
            "country_rules": country_rules,
            "rules": rules,
        }

    def _add_to_country(self, country_rules, country, rule_index):
        if country not in country_rules:
            country_rules[country] = []
        country_rules[country].append(rule_index)
        return country_rules

    def _match_url(self, website_id, url, country_code, state_code, rules_excluded):
        all_rules = self._get_active_rules()
        rules_id = all_rules["country_rules"].get(country_code, [])

        rules_matched = []
        for rule_index in rules_id:
            rule = all_rules["rules"][rule_index]
            if (
                (
                    (country_code, state_code) in rule["state_codes"]
                    or (country_code, False) in rule["state_codes"]
                )
                and (not rule["website_id"] or rule["website_id"] == website_id)
                and str(rule["id"]) not in rules_excluded
                and re.search(rule["regex"], url)
            ):
                rules_matched.append(rule)
        return rules_matched

    @api.model
    def _process_lead_generation(self, autocommit=True):
        _logger.info("Start Reveal Lead Generation")
        self.env["crm.reveal.view"]._clean_reveal_views()
        self._unlink_unrelevant_reveal_view()
        reveal_views = self._get_reveal_views_to_process()
        view_count = 0
        while reveal_views:
            view_count += len(reveal_views)
            server_payload = self._prepare_iap_payload(dict(reveal_views))
            enough_credit = self._perform_reveal_service(server_payload)
            if autocommit:
                self.env.cr.commit()
            if enough_credit:
                reveal_views = self._get_reveal_views_to_process()
            else:
                reveal_views = False
        _logger.info("End Reveal Lead Generation - %s views processed", view_count)

    @api.model
    def _unlink_unrelevant_reveal_view(self):
        months_valid = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("reveal.lead_month_valid", DEFAULT_REVEAL_MONTH_VALID)
        )
        try:
            months_valid = int(months_valid)
        except ValueError:
            months_valid = DEFAULT_REVEAL_MONTH_VALID
        domain = []
        domain.append(("reveal_ip", "!=", False))
        domain.append(
            (
                "create_date",
                ">",
                fields.Datetime.to_string(
                    datetime.date.today() - relativedelta(months=months_valid)
                ),
            )
        )
        leads = self.env["crm.lead"].with_context(active_test=False).search(domain)
        self.env["crm.reveal.view"].search(
            [("reveal_ip", "in", [lead.reveal_ip for lead in leads])]
        ).unlink()

    @api.model
    def _get_reveal_views_to_process(self):
        batch_limit = DEFAULT_REVEAL_BATCH_LIMIT
        query = """
            SELECT v.reveal_ip, array_agg(v.reveal_rule_id ORDER BY r.sequence)
            FROM crm_reveal_view v
            INNER JOIN crm_reveal_rule r
            ON v.reveal_rule_id = r.id
            WHERE v.reveal_state='to_process'
            GROUP BY v.reveal_ip
            LIMIT %s
            """

        self.env.cr.execute(query, [batch_limit])
        return self.env.cr.fetchall()

    def _prepare_iap_payload(self, pgv):
        new_list = list(set(itertools.chain.from_iterable(pgv.values())))
        rule_records = self.browse(new_list)
        return {"ips": pgv, "rules": rule_records._get_rules_payload()}

    def _get_rules_payload(self):
        company_country = self.env.company.country_id
        rule_payload = {}
        for rule in self:
            reveal_ids = [
                reveal_id.strip()
                for reveal_ids in rule.mapped("industry_tag_ids.reveal_ids")
                for reveal_id in reveal_ids.split(",")
            ]
            data = {
                "rule_id": rule.id,
                "lead_for": rule.lead_for,
                "countries": rule.country_ids.mapped("code"),
                "filter_on_size": rule.filter_on_size,
                "company_size_min": rule.company_size_min,
                "company_size_max": rule.company_size_max,
                "industry_tags": reveal_ids,
                "user_country": (company_country and company_country.code) or False,
            }
            if rule.lead_for == "people":
                data.update(
                    {
                        "contact_filter_type": rule.contact_filter_type,
                        "preferred_role": rule.preferred_role_id.reveal_id or "",
                        "other_roles": rule.other_role_ids.mapped("reveal_id"),
                        "seniority": rule.seniority_id.reveal_id or "",
                        "extra_contacts": rule.extra_contacts - 1,
                    }
                )
            rule_payload[rule.id] = data
        return rule_payload

    def _perform_reveal_service(self, server_payload):
        result = False
        account = self.env["iap.account"].get("reveal")
        params = {"account_token": account.sudo().account_token, "data": server_payload}
        result = self._iap_contact_reveal(params, timeout=300)

        all_ips, done_ips = list(server_payload["ips"].keys()), []
        for res in result.get("reveal_data", []):
            done_ips.append(res["ip"])
            if not res.get("not_found"):
                self._create_lead_from_response(res)
                self.env["crm.reveal.view"].search(  # noqa: E8507 - one lookup per revealed ip of the response
                    [("reveal_ip", "=", res["ip"])]
                ).unlink()
            else:
                views = self.env["crm.reveal.view"].search(  # noqa: E8507 - one lookup per revealed ip of the response
                    [("reveal_ip", "=", res["ip"])]
                )
                views.write({"reveal_state": "not_found"})
                views.flush_recordset()

        if result.get("credit_error"):
            _debug.logic("reveal_refused", reason="no_credit")
            self.env["crm.iap.lead.helpers"]._notify_no_more_credit(
                "reveal", self._name, "reveal.already_notified"
            )
            return False
        else:
            views = self.env["crm.reveal.view"].search(
                [("reveal_ip", "in", [ip for ip in all_ips if ip not in done_ips])]
            )
            views.write({"reveal_state": "not_found"})
            views.flush_recordset()
            self.env["ir.config_parameter"].sudo().set_param(
                "reveal.already_notified", False
            )
        return True

    def _iap_contact_reveal(self, params, timeout=300):
        endpoint = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("reveal.endpoint", DEFAULT_ENDPOINT)
            + "/iap/clearbit/1/reveal"
        )
        return iap_tools.iap_jsonrpc(
            endpoint, params=params, timeout=timeout, env=self.env
        )

    def _create_lead_from_response(self, result):
        if result["rule_id"]:
            rule = self.browse(result["rule_id"])
        else:
            return False
        if not result["clearbit_id"]:
            return False
        already_created_lead = self.env["crm.lead"].search_count(
            [("reveal_id", "=", result["clearbit_id"])], limit=1
        )
        if already_created_lead:
            _logger.info(
                "Existing lead for this clearbit_id [%s]", result["clearbit_id"]
            )
            return False
        lead_vals = rule._lead_vals_from_response(result)

        lead = self.env["crm.lead"].create(lead_vals)

        template_values = result["reveal_data"]
        template_values.update(
            {
                "flavor_text": _("Opportunity created by Odoo Lead Generation"),
                "people_data": result.get("people_data"),
            }
        )
        lead.message_post_with_source(
            "iap_mail.enrich_company",
            render_values=template_values,
            subtype_xmlid="mail.mt_note",
        )

        return lead

    def _lead_vals_from_response(self, result):
        self.check_singleton()
        company_data = result["reveal_data"]
        people_data = result.get("people_data")
        lead_vals = self.env["crm.iap.lead.helpers"].lead_vals_from_response(
            self.lead_type,
            self.team_id.id,
            self.tag_ids.ids,
            self.user_id.id,
            company_data,
            people_data,
        )

        lead_vals.update(
            {
                "priority": self.priority,
                "reveal_ip": result["ip"],
                "reveal_rule_id": self.id,
                "referred": "Website Visitor",
                "reveal_iap_credits": result["credit"],
            }
        )

        if self.suffix:
            lead_vals["name"] = "%s - %s" % (lead_vals["name"], self.suffix)

        return lead_vals
