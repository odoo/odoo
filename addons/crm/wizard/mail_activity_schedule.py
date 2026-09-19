# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import api, fields, models


class MailActivitySchedule(models.TransientModel):
    _inherit = "mail.activity.schedule"

    lead_id = fields.Many2one(
        "crm.lead",
        compute="_compute_lead_id",
        store=False,
        readonly=False,
    )
    lead_id_domain = fields.Char(
        compute="_compute_lead_id_domain",
        export_string_translation=False,
    )

    @api.depends_context("log_contact_id", "log_channel_partner_ids")
    def _compute_lead_id_domain(self):
        if contact := self._get_log_filter_contact():
            lead_id_domain = contact.commercial_partner_id._get_contact_opportunities_domain()
        else:
            lead_id_domain = []
        self.lead_id_domain = lead_id_domain

    def _get_res_model_fields(self):
        return {**super()._get_res_model_fields(), "crm.lead": "lead_id"}

    def _selection_res_model(self):
        res = super()._selection_res_model()
        if self.env.user.has_group("sales_team.group_sale_salesman"):
            res += [("crm.lead", self.env._("Lead/Opportunity"))]
        return res

    @api.depends("res_model_selection", "lead_id_domain")
    def _compute_lead_id(self):
        for schedule in self:
            if schedule.lead_id or schedule.res_model_selection != "crm.lead":
                continue
            domain = literal_eval(schedule.lead_id_domain)
            schedule.lead_id = self.env.context.get("default_lead_id") or self._get_log_default_record(
                "crm.lead", domain,
            )
