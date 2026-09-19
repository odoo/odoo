from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .survey_question import _check_appointment_write_access


class SurveyUserInput(models.Model):
    _inherit = "survey.user_input"

    appointment_type_id = fields.Many2one(
        comodel_name="appointment.type",
        index=True,
        ondelete="cascade",
    )
    calendar_event_id = fields.Many2one(
        comodel_name="calendar.event",
        index=True,
        copy=False,
        ondelete="cascade",
    )

    @api.constrains("appointment_type_id", "calendar_event_id", "survey_id")
    def _check_appointment_response(self):
        for response in self:
            if response.appointment_type_id:
                if response.survey_id or not response._has_appointment_owner():
                    raise ValidationError(
                        self.env._(
                            "An appointment response must belong to a meeting or a booking, without a survey."
                        )
                    )
                if (
                    response.calendar_event_id
                    and response.calendar_event_id.appointment_type_id
                    != response.appointment_type_id
                ):
                    raise ValidationError(
                        self.env._(
                            "The response and meeting must belong to the same appointment type."
                        )
                    )
            elif response.calendar_event_id:
                raise ValidationError(
                    self.env._("An appointment response requires an appointment type.")
                )

    @api.constrains("appointment_type_id", sudo=False)
    def _check_appointment_response_access(self):
        if self.filtered("appointment_type_id"):
            _check_appointment_write_access(self.env)

    def _has_appointment_owner(self):
        self.check_singleton()
        return bool(self.calendar_event_id)


class SurveyUserInputLine(models.Model):
    _inherit = "survey.user_input.line"

    appointment_type_id = fields.Many2one(
        related="user_input_id.appointment_type_id",
    )
    calendar_event_id = fields.Many2one(  # noqa: E8529  One2many inverse
        related="user_input_id.calendar_event_id",
        store=True,
        index=True,
    )
    partner_id = fields.Many2one(
        related="user_input_id.partner_id",
    )
    question_type = fields.Selection(related="question_id.question_type")

    @api.constrains("user_input_id", sudo=False)
    def _check_appointment_answer_access(self):
        if self.filtered("appointment_type_id"):
            _check_appointment_write_access(self.env)
