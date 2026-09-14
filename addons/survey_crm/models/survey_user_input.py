from markupsafe import Markup, escape

from odoo import _, fields, models


class SurveyUser_Input(models.Model):
    _inherit = "survey.user_input"

    lead_id = fields.Many2one(
        comodel_name="crm.lead",
        ondelete="set null",
    )

    def _mark_done(self):
        super()._mark_done()

        user_inputs = self.filtered(
            lambda user_input: (
                user_input.survey_id.survey_type in ["survey", "live_session", "custom"]
            )
        )
        user_inputs._create_leads_from_generative_answers()

    def _create_leads_from_generative_answers(self):
        user_inputs_generating_leads = self.filtered(
            lambda user_input: any(
                answer.generate_lead
                for answer in user_input.user_input_line_ids.suggested_answer_id
            )
        )
        user_inputs_grouped_by_survey = user_inputs_generating_leads.grouped(
            "survey_id"
        )
        lead_create_vals = {}
        for survey, user_inputs in user_inputs_grouped_by_survey.items():
            survey_lead_values = self._prepare_common_survey_lead_values(survey)
            for user_input in user_inputs:
                lead_create_vals[user_input] = (
                    user_input._prepare_user_input_lead_values() | survey_lead_values
                )
        if lead_create_vals:
            leads = self.env["crm.lead"].sudo().create(list(lead_create_vals.values()))
            for user_input, lead in zip(lead_create_vals.keys(), leads):
                user_input.lead_id = lead

    def _prepare_common_survey_lead_values(self, survey):
        salesperson = self.env["res.users"]
        sales_team = survey.team_id or self.env["team.team"]
        if sales_team:
            salesperson = (
                self.survey_id.user_id
                if survey.team_id in self.survey_id.user_id.sudo().sale_team_ids
                else self.env["res.users"]
            )
            if not salesperson:
                salesperson = survey.team_id.user_id or self.env["res.users"]

        return {
            "medium_id": self.env["utm.medium"]._get_or_create_utm_medium("Survey").id,
            "origin_survey_id": survey.id,
            "source_id": self.env["mixin.utm"]
            ._get_or_create_record("utm.source", survey.title)
            .id,
            "team_id": sales_team.id,
            "type": "opportunity",
            "user_id": salesperson.id,
        }

    def _prepare_user_input_lead_values(self):
        self.check_singleton()
        input_lead_values = self._prepare_lead_values_from_user_input_lines()

        username = participant_name = self.partner_id.name or self.partner_id.email
        if not username:
            participant_name = (
                input_lead_values["user_nickname"]
                or input_lead_values["public_user_mail"]
                or _("New")
            )
        lead_contact_name = username or input_lead_values["user_nickname"]
        lead_title = _(
            "%(participant_name)s %(category_name)s results",
            participant_name=participant_name,
            category_name=_("live session") if self.is_session_answer else _("survey"),
        )

        lead_values = {
            "contact_name": lead_contact_name,
            "description": input_lead_values["description"],
            "name": lead_title,
        }

        if self.partner_id.active:
            lead_values["partner_id"] = self.partner_id.id
        elif input_lead_values["public_user_mail"]:
            lead_values["email_from"] = input_lead_values["public_user_mail"]

        return lead_values

    def _prepare_lead_values_from_user_input_lines(self):
        self.check_singleton()

        answers_by_question = self.user_input_line_ids.grouped("question_id")
        html_input_lines = []
        line_break_indented_markuped = Markup("<br/>&emsp;")
        user_nickname = public_user_mail = ""
        for question, input_lines in answers_by_question.items():
            answers, last_row = [], ""
            initial_indent, multiple_answers = False, False
            input_lines_not_skipped = input_lines.filtered(
                lambda line: not line.skipped
            )
            if len(input_lines_not_skipped) == 0:
                answers = [Markup(" — <i>%(skipped)s</i>") % {"skipped": _("Skipped")}]
            for input_line_index, input_line in enumerate(input_lines_not_skipped):
                if question.question_type == "char_box":
                    if not user_nickname and question.save_as_nickname:
                        user_nickname = input_line._get_answer_value()
                    if not public_user_mail and question.validation_email:
                        public_user_mail = input_line._get_answer_value()
                    answers.append(
                        Markup(" %(separator)s %(answer)s")
                        % {
                            "separator": "—",
                            "answer": input_line._get_answer_value(),
                        }
                    )

                elif (
                    question.question_type == "matrix"
                    and (row := input_line.matrix_row_id)
                    and (col_value := input_line.suggested_answer_id.display_name)
                    and (last_row != row)
                ):
                    initial_indent = True
                    last_row = row
                    answers.append(
                        Markup("%(row_name)s — %(col_value)s")
                        % {
                            "row_name": row.display_name,
                            "col_value": col_value,
                        }
                    )
                elif question.question_type == "matrix" and row:
                    answers[-1] += Markup(", %(col_value)s") % {"col_value": col_value}
                elif question.question_type == "matrix" and not row:
                    initial_indent = True
                    answers.append(
                        Markup(
                            "<i><b>%(comment)s</b></i> — %(comment_answer)s"
                            % {
                                "comment": _("Comment"),
                                "comment_answer": escape(
                                    input_line._get_answer_value()
                                ).replace("\n", line_break_indented_markuped),
                            }
                        )
                    )

                elif question.question_type in [
                    "numerical_box",
                    "scale",
                    "date",
                    "datetime",
                ]:
                    answers.append(
                        Markup(" %(separator)s %(answer)s")
                        % {
                            "separator": "—",
                            "answer": str(input_line._get_answer_value()),
                        }
                    )

                elif (
                    question.question_type in ["simple_choice", "multiple_choice"]
                    and input_line.answer_type == "char_box"
                ):
                    answers.append(
                        Markup(
                            "%(line_break_indented_markuped)s<i><b>%(comment)s</b></i> — %(answer)s"
                        )
                        % {
                            "line_break_indented_markuped": line_break_indented_markuped
                            if multiple_answers or len(input_lines_not_skipped) == 1
                            else "",
                            "comment": _("Comment"),
                            "answer": escape(
                                str(input_line._get_answer_value())
                            ).replace("\n", line_break_indented_markuped),
                        }
                    )
                elif question.question_type in ["simple_choice", "multiple_choice"]:
                    multiple_answers = input_line_index != 0
                    answer = str(input_line._get_answer_value())
                    if (
                        input_line.suggested_answer_id
                        and not input_line._get_answer_value()
                    ):
                        answer = (
                            input_line.suggested_answer_id.value_image_filename or ""
                        )
                    answers.append(
                        Markup("%(separator)s %(answer)s")
                        % {
                            "separator": " —" if not multiple_answers else ",",
                            "answer": answer,
                        }
                    )

                elif question.question_type == "text_box":
                    answers = [
                        "",
                        Markup(
                            "%(text)s"
                            % {
                                "text": escape(input_line._get_answer_value()).replace(
                                    "\n", line_break_indented_markuped
                                )
                            }
                        ),
                    ]

            html_input_lines.append(
                Markup("<li>%(question_title)s%(initial_indent)s%(user_inputs)s</li>")
                % {
                    "question_title": escape(question.title),
                    "initial_indent": line_break_indented_markuped
                    if initial_indent
                    else "",
                    "user_inputs": Markup("").join(answers)
                    if multiple_answers
                    else line_break_indented_markuped.join(answers),
                }
            )

        description = Markup("<div>%(answers)s:</div><ul>%(survey_answers)s</ul>") % {
            "answers": _("Answers"),
            "survey_answers": Markup("").join(html_input_lines),
        }
        return {
            "description": description,
            "user_nickname": user_nickname,
            "public_user_mail": public_user_mail,
        }

    def action_redirect_lead(self):
        self.check_singleton()
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "crm.crm_lead_opportunities"
        )
        action["views"] = [((self.env.ref("crm.crm_lead_view_form").id), "form")]
        action["res_id"] = self.lead_id.id
        return action
