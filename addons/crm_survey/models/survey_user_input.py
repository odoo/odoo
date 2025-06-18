from odoo import models


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
        """ This method will check and prepare lead fields data for an eventual new opportunity. """
        for user_input in self:
            is_lead_answer, user_nickname, public_user_mail, description = False, False, None, "Answers:<ul>"
            current_question, first_answer, first_question = None, True, True
            for answer_id in user_input.user_input_line_ids:
                ### Write the lead description (in HTML format)
                # Write question to the description
                question = answer_id.question_id.title
                if question != current_question:
                    current_question = question
                    first_answer = True
                    if first_question:
                        description += f"<li>{current_question}"
                        first_question = False
                    else:
                        description += f"</li><li>{current_question}"

                # Write answer(s) to the question
                # Skipped question
                if answer_id.skipped:
                    description += " — <i> Skipped</i>"
                    continue
                # Long text box
                if answer_id.question_id.question_type == "text_box":
                    answer = "<br/>&emsp;" + answer_id._get_answer_value().replace('\n', "<br/>&emsp;")
                    description += str(answer)
                # Matrix
                elif answer_id.question_id.question_type == "matrix":
                    row_value = answer_id.matrix_row_id.display_name
                    col_value = answer_id.suggested_answer_id.display_name
                    description += '<br/>&emsp;' + f"{row_value} — {col_value}"
                # Others
                else:
                    if first_answer:
                        description += " — "
                    answer = answer_id.display_name
                    if first_answer:
                        description += str(answer)
                        first_answer = False
                    else:
                        description += ', ' + str(answer)

                # Check if answer should create a lead
                if not is_lead_answer and answer_id.suggested_answer_id and answer_id.suggested_answer_id.is_create_lead:
                    is_lead_answer = True
                # Check if the question has a nickname recorded
                if answer_id.question_id.save_as_nickname:
                    user_nickname = answer
                # Check if the question has a email answer
                if answer_id.question_id.validation_email:
                    public_user_mail = answer
            description += "</li></ul>"

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
