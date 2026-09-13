from odoo import api, fields, models


class EventRegistrationAnswer(models.Model):
    """Represents the user input answer for a single event.question"""

    _name = "event.registration.answer"
    _description = "Event Registration Answer"
    _rec_names_search = ["value_answer_id", "value_text_box"]

    question_id = fields.Many2one(
        comodel_name="event.question",
        required=True,
        domain="[('event_ids', 'in', event_id)]",
        ondelete="restrict",
    )
    registration_id = fields.Many2one(
        comodel_name="event.registration",
        index=True,
        required=True,
        ondelete="cascade",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        related="registration_id.partner_id",
    )
    event_id = fields.Many2one(
        comodel_name="event.event",
        related="registration_id.event_id",
    )
    question_type = fields.Selection(related="question_id.question_type")
    value_answer_id = fields.Many2one(
        comodel_name="event.question.answer",
        string="Suggested answer",
    )
    value_text_box = fields.Text(string="Text answer")

    _value_check = models.Constraint(
        "CHECK(value_answer_id IS NOT NULL OR COALESCE(value_text_box, '') <> '')",
        "There must be a suggested value or a text value.",
    )

    # for displaying selected answers by attendees in attendees list view
    @api.depends("value_answer_id", "question_type", "value_text_box")
    def _compute_display_name(self):
        for reg in self:
            reg.display_name = (
                reg.value_answer_id.name
                if reg.question_type == "simple_choice"
                else reg.value_text_box
            )
