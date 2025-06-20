from markupsafe import Markup, escape
from odoo import models, _


class SurveyUser_Input(models.Model):
    _inherit = "survey.user_input"

    def _mark_done(self):
        """ Check if we need to create a lead on answer submission, except for live sessions.

            (note: Here, we are going to filter the surveys submitted at the end by the user according to type.
            However, the live_session and custom types are present in the filter below.
            Their presence here corresponds to the case where a survey has simply been shared
            (as for the classic 'survey' type) without there being a live session.
            In this case, it is when the user has finally submitted the survey.
            Otherwise, if the submission is due from the host of a live session, this function is not called.
            So, please refer to the action_end_session function in survey.survey.)
        """
        super()._mark_done()

        # Generate lead
        user_inputs = self.filtered(lambda user_input:
            user_input.survey_id.survey_type in ['survey', 'live_session', 'custom']
        )
        user_inputs._create_leads_if_generative_answers()

    def _create_leads_if_generative_answers(self):
        """ This method will prepare lead fields data for an eventual new opportunity. """
        user_inputs_grouped_by_survey = self.grouped('survey_id')
        for survey_id in user_inputs_grouped_by_survey:
            user_input_ids = user_inputs_grouped_by_survey[survey_id]
            lead_create_vals = []
            for user_input_id in user_input_ids:
                user_input_id._prepare_lead_values_and_check_generative_answers(lead_create_vals)
            odoobot = self.env.ref('base.user_root')
            self.env['crm.lead'].with_user(odoobot).create(lead_create_vals)

    def _prepare_lead_values_and_check_generative_answers(self, lead_create_vals):
        """ This method checks if at least, one lead answer has been submitted.
            In that case, all lead values necessary (in a dictionary) are added to the array in argument.
            To write the description (notes in CRM) in HTML format, there are 5 cases:
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
        self.ensure_one()
        line_break_with_indentation_tags = "<br/>&emsp;"
        answers_grouped_by_question = self.user_input_line_ids.grouped('question_id')
        html_input_lines = []
        is_lead_answer, user_nickname, public_user_mail = False, "", ""
        for question_id, input_lines in answers_grouped_by_question.items():
            tag_begin, question_title, separator, tag_end = "<li>", question_id.title, "", "</li>"
            answer_tag_begin, answer_description, answer_tag_end = "", "", ""
            first_answer, last_row_value = True, ""
            if not input_lines[0].skipped:
                for answer_id in input_lines:
                    if question_id.question_type == "text_box":
                        answer_tag_begin = line_break_with_indentation_tags
                        answer_description = answer_id._get_answer_value()
                    elif question_id.question_type == "matrix":
                        row_value = answer_id.matrix_row_id.display_name
                        col_value = answer_id.suggested_answer_id.display_name
                        if row_value:
                            if last_row_value != row_value:
                                last_row_value = row_value
                                answer_description += f"{line_break_with_indentation_tags}{_('%s', row_value)} — {_('%s', col_value)}"
                            else:  # For multiple suggested answers
                                answer_description += f", {_('%s', col_value)}"
                        else:  # Comment field
                            comment_answer = answer_id._get_answer_value()
                            answer_description += f"{line_break_with_indentation_tags}{_('Comment')} — {escape(_('%s', comment_answer))}"
                    else:
                        separator = " — "
                        answer_description += "" if first_answer else ", "   # For multiple suggested answers
                        answer_description += answer_id.display_name
                        first_answer = False

                    is_lead_answer, user_nickname, public_user_mail = self._check_lead_flag_nickname_mail(
                        is_lead_answer, user_nickname, public_user_mail, question_id, answer_id)
            else:
                # To write "Skipped" in italic
                separator = " — "
                answer_tag_begin, answer_tag_end = "<i>", "</i>"
                answer_description = "Skipped"  # Note: The answer's display name already contains this word, we just go ahead here

            question_title = _("%s", question_title)
            answer_description = escape(_("%s", answer_description)) if question_id.question_type != "matrix" else answer_description
            answer_description = answer_description.replace('\n', Markup("%s" % (line_break_with_indentation_tags)))  # To keep line HTML breaks
            questions_with_answers_description = Markup("%s%s%s%s%s%s%s" %
                (tag_begin, question_title, separator, answer_tag_begin, answer_description, answer_tag_end, tag_end)
            )
            html_input_lines.append(questions_with_answers_description)

        description = Markup("%s%s%s" % (f"{_('Answers')}:<ul>", ''.join(html_input_lines), "</ul>"))
        if is_lead_answer:
            self._prepare_user_input_lead_values(description, user_nickname, public_user_mail, lead_create_vals)

    def _prepare_user_input_lead_values(self, description, user_nickname, public_user_mail, lead_create_vals):
        """ This method will prepare the dictionary for making the lead """
        self.ensure_one()
        medium = self.env['utm.medium']._fetch_or_create_utm_medium('Survey')

        source = self.env['utm.source'].search([('name', '=', self.survey_id.title)])
        if not source:
            source = self.env['utm.source'].create({'name': self.survey_id.title})

        # Check if the survey responsible is from, at least, a sales team
        survey_responsible = self.survey_id.user_id
        if survey_responsible and not self.env['crm.team'].search([('member_ids', 'in', survey_responsible.ids)]):
            survey_responsible = self.env['res.users']

        # Get the username
        username = self.partner_id.name
        if not username:  # Public user
            username = "Participant#" + str(self.id)
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
        if self.partner_id.id:
            lead_dictionary['partner_id'] = self.partner_id.id
        else:  # Save email field answer otherwise
            lead_dictionary['email_from'] = public_user_mail

        lead_create_vals.append(lead_dictionary)

    def _check_lead_flag_nickname_mail(self, is_lead_answer, user_nickname, public_user_mail, question_id, answer_id):
        self.ensure_one()
        # Check if answer should create a lead
        if not is_lead_answer and answer_id.suggested_answer_id and answer_id.suggested_answer_id.is_create_lead:
            is_lead_answer = True
        # Check if the question has a nickname recorded
        if not user_nickname and question_id.save_as_nickname:
            user_nickname = answer_id.display_name
        # Check if the question has a email answer
        if not public_user_mail and question_id.validation_email:
            public_user_mail = answer_id.display_name

        return is_lead_answer, user_nickname, public_user_mail
