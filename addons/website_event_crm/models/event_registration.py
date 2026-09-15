from markupsafe import Markup

from odoo import _, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class EventRegistration(models.Model):
    _inherit = "event.registration"

    def _get_lead_description_registration(self, line_suffix=""):
        reg_description = super()._get_lead_description_registration(
            line_suffix=line_suffix
        )
        if not self.registration_answer_ids:
            _debug.logic("lead_description_without_answers", registration=self)
            return reg_description

        answer_descriptions = []
        for answer in self.registration_answer_ids:
            answer_value = (
                answer.value_answer_id.name
                if answer.question_type == "simple_choice"
                else answer.value_text_box
            )
            answer_value = Markup("<br/>").join(
                ["    %s" % line for line in answer_value.split("\n")]
            )
            answer_descriptions.append(
                Markup("  - %s<br/>%s") % (answer.question_id.title, answer_value)
            )
        _debug.pipeline(
            "lead_description_with_answers",
            registration=self,
            answers=self.registration_answer_ids,
        )
        return Markup("%s%s<br/>%s") % (
            reg_description,
            _("Questions"),
            Markup("<br/>").join(answer_descriptions),
        )

    def _get_fields_lead_description(self):
        res = super()._get_fields_lead_description()
        res.append("registration_answer_ids")
        return res

    def _prepare_lead_vals(self, rule):
        lead_values = super()._prepare_lead_vals(rule)
        if self.visitor_id:
            lead_values["visitor_ids"] = self.visitor_id
        if self.visitor_id.lang_id:
            lead_values["lang_id"] = self.visitor_id.lang_id[0].id
        _debug.logic(
            "registration_lead_values",
            registration=self,
            visitor=self.visitor_id,
            lang=self.visitor_id.lang_id[:1],
        )
        return lead_values
