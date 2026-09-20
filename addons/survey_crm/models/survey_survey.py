from odoo import api, fields, models


class SurveySurvey(models.Model):
    _inherit = "survey.survey"

    generate_lead = fields.Boolean(
        string="Lead Generating",
        compute="_compute_generate_lead",
        store=True,
    )
    lead_count = fields.Integer(
        string="Leads",
        compute="_compute_lead_count",
        help="Number of leads created by this survey",
    )
    lead_ids = fields.One2many(
        comodel_name="crm.lead",
        inverse_name="origin_survey_id",
    )
    team_id = fields.Many2one(
        comodel_name="team.team",
        string="Assign Leads to",
        index="btree_not_null",
        domain=[("use_sale", "=", True)],
        ondelete="set null",
    )

    @api.depends("survey_type", "question_ids")
    def _compute_generate_lead(self):
        for survey in self:
            survey.generate_lead = survey.survey_type in [
                "survey",
                "live_session",
                "custom",
            ] and any(question_id.generate_lead for question_id in survey.question_ids)

    @api.depends("lead_ids")
    def _compute_lead_count(self):
        if self.ids and self.env["crm.lead"].has_access("read"):
            leads = self.env["crm.lead"]._read_group(
                [("origin_survey_id", "in", self.ids)],
                ["origin_survey_id"],
                ["__count"],
            )
            leads_count_by_survey = {survey.id: count for survey, count in leads}
            for survey in self:
                survey.lead_count = leads_count_by_survey.get(survey.id, 0)
        else:
            self.lead_count = 0

    def action_end_session(self):
        super().action_end_session()

        user_inputs = self.user_input_ids.filtered(
            lambda user_input: user_input.create_date >= self.session_start_time
        )
        user_inputs._create_leads_from_generative_answers()

    def action_survey_see_leads(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "crm.crm_lead_all_leads"
        )
        action["context"] = dict(
            self.env["ir.actions.actions"]._eval_action_context(
                action.get("context", "{}").strip()
            ),
            create=False,
        )
        action["domain"] = [("origin_survey_id", "in", self.ids)]
        return action
