from markupsafe import Markup
from odoo import models, _


class SurveyUser_Input(models.Model):
    _inherit = "survey.user_input"

    def _mark_done(self):
        """ Check if we need to create a lead on answer submission, except for live sessions """
        super()._mark_done()

        # Generate lead
        # (note: Here, we are going to filter the surveys submitted at the end by the user according to type.
        # However, the live_session and custom types are present in the filter below.
        # Their presence here corresponds to the case where a survey has simply been shared
        # (as for the classic 'survey' type) without there being a live session.
        # In this case, it is the user who has finally submitted the survey.
        # Otherwise, if the submission is due from the host of a live session, this function is not called.
        # In this case, refer to the action_end_session function in survey.survey.)
        user_inputs = self.filtered(lambda user_input:
            user_input.survey_id.survey_type in ['survey', 'live_session', 'custom']
        )
        user_inputs._create_lead_if_generative_answer()

    def _create_lead_if_generative_answer(self):
        """ This method will check and prepare lead fields data for an eventual new opportunity.
            Here are 5 cases:
                - Suggested answers question: Question — Answer 1, Answer 3
                    (==> expected html line: <li>Question: — Answer 1, Answer 3</li>)
                - Matrix question: Question
                                    Line label 1 — Answer 1
                                    Line label 1 — Answer 3
                                    Line label 4 — Answer 2
                    (==> expected html line: <li>
                                                Question:
                                                <br>&esmpLine label 1 — Answer 1
                                                <br>&esmpLine label 1 — Answer 3
                                                <br>&esmpLine label 4 — Answer 2
                                             </li>)
                - Long text question: Question
                    (==> expected html line: <li>
                                                Question:
                                                <br>&esmpText line 1
                                                <br>&esmpText line 2
                                                <br>&esmpText line 3
                                             </li>)
                - Other types : Question — Answer
                    (==> expected html line: <li>Question: — Answer</li>)
                - Skipped question: Question — Skipped
                    (==> expected html line: <li>Question: — <i>Skipped</i></li>)
        """
        line_break_with_indentation_tags = "<br/>&emsp;"
        for user_input in self:
            is_lead_answer, user_nickname, public_user_mail = False, False, None
            html_input_lines = []
            answers_grouped_by_question = user_input.user_input_line_ids.grouped('question_id')
            for question_id, input_lines in answers_grouped_by_question.items():
                tag_begin, question_title, separator, tag_end = "<li>", question_id.title, "", "</li>"
                answer_tag_begin, answer_description, answer_tag_end = "", "", ""
                first_answer = True
                if not input_lines[0].skipped:
                    for answer_id in input_lines:
                        if question_id.question_type == "text_box":
                            answer_tag_begin = line_break_with_indentation_tags
                            answer_description = answer_id._get_answer_value().replace('\n', f"{line_break_with_indentation_tags}")
                        elif question_id.question_type == "matrix":
                            row_value = answer_id.matrix_row_id.display_name
                            col_value = answer_id.suggested_answer_id.display_name
                            answer_description += f"{line_break_with_indentation_tags}{row_value} — {col_value}"
                        else:
                            separator = " — "
                            answer_description += "" if first_answer else ", "
                            answer_description += answer_id.display_name
                            first_answer = False

                        # Check if answer should create a lead
                        if not is_lead_answer and answer_id.suggested_answer_id and answer_id.suggested_answer_id.is_create_lead:
                            is_lead_answer = True
                        # Check if the question has a nickname recorded
                        if not user_nickname and question_id.save_as_nickname:
                            user_nickname = answer_id.display_name
                        # Check if the question has a email answer
                        if not public_user_mail and question_id.validation_email:
                            public_user_mail = answer_id.display_name
                else:
                    # To write "Skipped" in italic
                    separator = " — "
                    answer_tag_begin, answer_tag_end = "<i>", "</i>"
                    answer_description = input_lines[0].display_name  # Note: The answer's display name already contains the word

                question_title = _("%s", question_title)
                answer_description = _("%s", answer_description)
                questions_with_answers_description = f"{tag_begin}{question_title}{separator}{answer_tag_begin}{answer_description}{answer_tag_end}{tag_end}"
                questions_with_answers_description = Markup(
                    "%s%s%s%s%s%s%s" %
                    (tag_begin, question_title, separator, answer_tag_begin, answer_description, answer_tag_end, tag_end)
                )
                html_input_lines.append(questions_with_answers_description)

            description_begin = f"{_('Answers')}:<ul>"
            html_input_lines = ''.join(html_input_lines)
            description_end = "</ul>"
            description = f"{description_begin}{html_input_lines}{description_end}"

            ### Generate the lead
            if is_lead_answer:
                self._generate_lead(user_input, user_nickname, description, public_user_mail)

    def _generate_lead(self, user_input, user_nickname, description, public_user_mail):
        """ This method will:
        - generate an new opportunity
        - link that to the current survey
        """
        medium = self.env['utm.medium']._fetch_or_create_utm_medium('Survey')

        source = self.env['utm.source'].search([('name', '=', self.survey_id.title)])
        if not source:
            source = self.env['utm.source'].create({'name': self.survey_id.title})

        # Check if the survey responsible is from, at least, a sales team
        survey_responsible = user_input.survey_id.user_id
        if survey_responsible and not self.env['crm.team'].search([('member_ids', 'in', survey_responsible.ids)]):
            survey_responsible = self.env['res.users']

        # Get the username
        username = user_input.partner_id.name
        if not username:  # Public user
            username = "Participant#" + str(user_input.id)
            lead_title_start = "New"
            if user_nickname or public_user_mail:
                lead_title_start = f"{user_nickname or public_user_mail}'s"
        else:
            lead_title_start = f"{username}'s"

        lead_dictionary = {
            'contact_name': user_nickname or username,
            'description': description,
            'medium_id': medium.id,
            'name': f"{lead_title_start} survey results",
            'source_id': source.id,
            'survey_id': self.survey_id.id,
            'type': 'opportunity',
            'user_id': survey_responsible.id,
        }

        # Associate lead to the existing partner when known. Either because the person is connected
        # or because they received the survey with a unique token (by email for example).
        if user_input.partner_id.id:
            lead_dictionary['partner_id'] = user_input.partner_id.id
        else:  # Save email field answer otherwise
            lead_dictionary['email_from'] = public_user_mail

        odoobot = self.env.ref('base.user_root')
        self.env['crm.lead'].with_user(odoobot).create(lead_dictionary)  # Creating the lead
