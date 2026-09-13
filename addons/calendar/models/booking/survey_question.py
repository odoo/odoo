from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


def _check_appointment_write_access(env):
    # Write rules apply to the old owner; transitions must check the destination.
    # Call from sudo=False constraints to retain the caller's actual privileges.
    if not env.su and not env.user.has_group("calendar.group_appointment_manager"):
        raise AccessError(
            env._(
                "Only appointment administrators can edit appointment questions and answers."
            )
        )


class SurveyQuestion(models.Model):
    _inherit = "survey.question"

    appointment_type_ids = fields.Many2many(
        comodel_name="appointment.type",
        relation="appointment_type_survey_question_rel",
        column1="survey_question_id",
        column2="appointment_type_id",
        string="Appointment Types",
    )
    appointment_count = fields.Integer(
        string="# Appointments",
        compute="_compute_appointment_count",
    )
    is_default = fields.Boolean(
        string="Default question",
        help="Include by default in new appointment types.",
    )
    is_reusable = fields.Boolean(
        compute="_compute_is_reusable",
        default=True,
        store=True,
        readonly=False,
        help="Will appear in the list of available questions when adding one in any appointment. Always true for default questions.",
    )
    _check_default_question_is_reusable = models.Constraint(
        "CHECK(is_default IS DISTINCT FROM TRUE OR is_reusable IS TRUE)",
        "A default question must be reusable.",
    )

    @api.constrains(
        "question_type", "suggested_answer_ids", "appointment_type_ids", "is_default"
    )
    def _check_question_type(self):
        incomplete_questions = self.filtered(
            lambda question: (
                (question.appointment_type_ids or question.is_default)
                and question.question_type
                in ["dropdown", "simple_choice", "multiple_choice"]
                and not question.suggested_answer_ids
            )
        )
        if incomplete_questions:
            raise ValidationError(
                _(
                    "The following question(s) do not have any selectable answers : %s",
                    ", ".join(incomplete_questions.mapped("title")),
                )
            )

    @api.constrains("appointment_type_ids", "is_default", sudo=False)
    def _check_appointment_question_access(self):
        if self.filtered(
            lambda question: question.appointment_type_ids or question.is_default
        ):
            _check_appointment_write_access(self.env)

    @api.constrains(
        "survey_id", "appointment_type_ids", "question_type", "is_default", "is_page"
    )
    def _check_appointment_question(self):
        for question in self:
            if question.appointment_type_ids or question.is_default:
                if (
                    question.survey_id
                    or question.is_page
                    or question.question_type
                    not in (
                        "char_box",
                        "text_box",
                        "dropdown",
                        "simple_choice",
                        "multiple_choice",
                    )
                ):
                    raise ValidationError(
                        self.env._(
                            "Appointments require standalone text or choice questions."
                        )
                    )

    @api.depends("appointment_type_ids")
    def _compute_appointment_count(self):
        appointment_data = self.env["appointment.type"]._read_group(
            [("question_ids", "in", self.ids)], ["question_ids"], ["__count"]
        )
        mapped_data = {
            appointment_question.id: count
            for appointment_question, count in appointment_data
        }
        for question in self:
            if not question.id:  # new record
                question.appointment_count = len(question.appointment_type_ids)
            else:
                question.appointment_count = mapped_data.get(question.id, 0)

    @api.depends("is_default")
    def _compute_is_reusable(self):
        for question in self:
            if question.is_default:
                question.is_reusable = True

    def action_view_question_answer_inputs(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "calendar.appointment_answer_input_action"
        )
        modes = (
            ("pivot", "graph", "list", "form")
            if self.question_type in ("dropdown", "simple_choice", "multiple_choice")
            else ("list", "form")
        )
        action["views"] = [
            (
                self.env.ref(
                    f"calendar.appointment_answer_input_view_{'tree' if mode == 'list' else mode}"
                ).id,
                mode,
            )
            for mode in modes
        ]
        action["context"] = {
            "create": False,
            "search_default_question_id": self.id,
        }
        if appointment_id := self.env.context.get("search_default_appointment_type_id"):
            action["context"].update(search_default_appointment_type_id=appointment_id)
        return action

    def action_view_appointment_types(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "calendar.appointment_type_action"
        )
        action["domain"] = [("question_ids", "in", self.ids)]
        return action


class SurveyQuestionAnswer(models.Model):
    _inherit = "survey.question.answer"

    @api.constrains("question_id", sudo=False)
    def _check_appointment_choice_access(self):
        self.filtered(
            lambda answer: (
                answer.question_id.appointment_type_ids or answer.question_id.is_default
            )
        ).check_access("write")
