from markupsafe import Markup, escape

from odoo import fields, models, _


class SurveyUser_Input(models.Model):
    _inherit = 'survey.user_input'

    lead_id = fields.Many2one('crm.lead', ondelete='set null')  # Linked to, at most, one lead

    def _mark_done(self):
        ''' Check if we need to create a lead on answer submission, except for live sessions.

            (Note: This method is called when a response has been submitted to a survey.
            In this case, the filter enables to keep, before the verification, the user
            inputs that could create leads depending on the type of survey carried out.

            Yet, this method is NOT called when a real live/custom session ends (a live session
            survey can be shared without necessarily being live). In this case, please refer
            to the action_end_session function in survey.survey of this module.)
        '''
        super()._mark_done()

        # Generate lead
        user_inputs = self.filtered(lambda user_input:
            user_input.survey_id.survey_type in ['survey', 'live_session', 'custom']
        )
        user_inputs._create_leads_from_generative_answers()

    def _create_leads_from_generative_answers(self):
        ''' This method filters the user inputs in self to only keep those that create a lead.
            After a step of data preparation, create related leads in batch. '''
        user_inputs_generating_leads = self.filtered(lambda user_input:
            any(answer.generate_lead for answer in user_input.user_input_line_ids.suggested_answer_id))
        user_inputs_grouped_by_survey = user_inputs_generating_leads.grouped('survey_id')
        lead_create_vals = {}
        for survey, user_inputs in user_inputs_grouped_by_survey.items():
            survey_lead_values = self._prepare_common_survey_lead_values(survey)
            for user_input in user_inputs:
                lead_create_vals[user_input] = user_input._prepare_user_input_lead_values() | survey_lead_values
        # This if statement could be useless, but it prevents unnecessary
        # queries to the db if no lead needs to be created.
        if lead_create_vals:
            leads = self.env['crm.lead'].sudo().create(list(lead_create_vals.values()))
            for user_input, lead in zip(lead_create_vals.keys(), leads):
                user_input.lead_id = lead

    def _prepare_common_survey_lead_values(self, survey):
        salesperson = self.env['res.users']
        sales_team = survey.team_id or self.env['crm.team']
        if sales_team:
            # Check if the survey responsible is from the sales team provided to assign him as the salesperson.
            # The .sudo() is useful in cases where a live session is ended by someone who does not have access to leads.
            # In other cases, .super() already uses .sudo() on responses.
            salesperson = self.survey_id.user_id if survey.team_id in self.survey_id.user_id.sudo().crm_team_ids else self.env['res.users']
            if not salesperson:
                # Otherwise, assign to the team leader if applicable
                salesperson = survey.team_id.user_id or self.env['res.users']

        return {
            'medium_id': self.env['utm.medium']._fetch_or_create_utm_medium('Survey').id,
            'origin_survey_id': survey.id,
            'source_id': self.env['utm.mixin']._find_or_create_record('utm.source', survey.title).id,
            'team_id': sales_team.id,
            'type': 'opportunity',  # we assume that the lead is sufficiently qualified based on survey responses to be an opportunity
            'user_id': salesperson.id,
        }

    def _prepare_user_input_lead_values(self):
        ''' This method prepares the user values dictionary for creating the lead '''
        self.ensure_one()
        input_lead_values = self._prepare_lead_values_from_user_input_lines()

        # Get the username (or the email if the user was imported from a spreadsheet)
        username = participant_name = self.partner_id.name or self.partner_id.email
        if not username:  # Public user
            participant_name = input_lead_values['user_nickname'] or input_lead_values['public_user_mail'] or _('New')
        lead_contact_name = username or input_lead_values['user_nickname']
        lead_title = _('%(participant_name)s %(category_name)s results',
                       participant_name=participant_name, category_name=_('live session') if self.is_session_answer else _('survey'))

        lead_values = {
            'contact_name': lead_contact_name,
            'description': input_lead_values['description'],
            'name': lead_title,
        }

        # Associate lead to the existing partner when known. Either because the person is connected
        # or because they received the survey with a unique token (by email for example).
        if self.partner_id.active:  # active is used for a protection against odoobot and public user's partner
            lead_values['partner_id'] = self.partner_id.id
        elif input_lead_values['public_user_mail']:  # Save email field answer otherwise
            lead_values['email_from'] = input_lead_values['public_user_mail']

        return lead_values

    def _prepare_lead_values_from_user_input_lines(self):
        ''' This prepares dict-formatted lead values from user input lines. It formats
            lead description and get user's nickname and his email, if they're provided.
            To write the description (notes in CRM) in HTML format, there are 5 cases:
                - Suggested answers question: <li>Question — Answer 1, Answer 3</li>
                - Matrix question:  <li>
                                        Question
                                        <br/>&emsp;Line label 1 — Answer 1
                                        <br/>&emsp;Line label 1 — Answer 3
                                        <br/>&emsp;Line label 4 — Answer 2
                                    </li>
                - Long text question:   <li>
                                            Question
                                            <br/>&emsp;Text line 1
                                            <br/>&emsp;Text line 2
                                            <br/>&emsp;Text line 3
                                        </li>
                - Other types: <li>Question — Answer</li>
                - Skipped question: <li>Question — <i>Skipped</i></li>

            Note: '<br/>&emsp;' is used to get a line break with indentation
        '''
        self.ensure_one()

        answers_by_question = self.user_input_line_ids.grouped('question_id')
        html_input_lines = []
        line_break_indented_markuped = Markup('<br/>&emsp;')
        user_nickname = public_user_mail = ''
        for question, input_lines in answers_by_question.items():
            answers, last_row = [], ''
            # initial_indent is useful to manage matrix writing and multiple_answers for several suggested answers chosen
            initial_indent, multiple_answers = False, False
            # When no response is given, an input line is still created with the skipped field set to True.
            # However, if there is a comment (option for suggested answers question), another input line is
            # created with the comment (and skipped set to False).
            # In summary, the next recordset is empty when no response and no comment are left.
            input_lines_not_skipped = input_lines.filtered(lambda line: not line.skipped)
            if len(input_lines_not_skipped) == 0:
                answers = [Markup(' — <i>%(skipped)s</i>') % {'skipped': _('Skipped')}]
            for input_line_index, input_line in enumerate(input_lines_not_skipped):
                # Write description line according to the patterns explained above.
                # We usually write the question first, then the answer; but if we have several answers
                # for the same question, we continue the editing we have already started.
                # Note: Markup ensures the validity of HTML and we escape responses and labels that could
                # be a source of injection if applicable. Since the placeholder values are not in the Markup
                # constructor, this automatically escapes those fields.
                if question.question_type == 'char_box':
                    # Check if the question has a nickname recorded or an email answer
                    if not user_nickname and question.save_as_nickname:
                        user_nickname = input_line._get_answer_value()
                    if not public_user_mail and question.validation_email:
                        public_user_mail = input_line._get_answer_value()
                    answers.append(Markup(' %(separator)s %(answer)s') % {
                        'separator': '—',
                        'answer': input_line._get_answer_value(),
                    })

                elif question.question_type == 'matrix' and (row := input_line.matrix_row_id) and \
                    (col_value := input_line.suggested_answer_id.display_name) and (last_row != row):
                    initial_indent = True
                    last_row = row
                    answers.append(Markup('%(row_name)s — %(col_value)s') % {
                            'row_name': row.display_name,
                            'col_value': col_value,
                        })
                elif question.question_type == 'matrix' and row:  # For multiple suggested answers (complete last edition)
                    answers[-1] += Markup(', %(col_value)s') % {'col_value': col_value}
                elif question.question_type == 'matrix' and not row:  # Comment field
                    initial_indent = True
                    # Leave the placeholder values in the constructor to keep line break with indentation
                    answers.append(Markup('<i><b>%(comment)s</b></i> — %(comment_answer)s' % {
                        'comment': _('Comment'),
                        'comment_answer': escape(input_line._get_answer_value()).replace('\n', line_break_indented_markuped),
                        })
                    )

                elif question.question_type in ['numerical_box', 'scale', 'date', 'datetime']:
                    answers.append(Markup(' %(separator)s %(answer)s') % {
                        'separator': '—',
                        'answer': str(input_line._get_answer_value()),
                    })

                elif question.question_type in ['simple_choice', 'multiple_choice'] and input_line.answer_type == 'char_box':  # Comment case
                    answers.append(Markup('%(line_break_indented_markuped)s<i><b>%(comment)s</b></i> — %(answer)s') % {
                        'line_break_indented_markuped': line_break_indented_markuped if multiple_answers or len(input_lines_not_skipped) == 1 else '',
                        'comment': _('Comment'),
                        'answer': escape(str(input_line._get_answer_value())).replace('\n', line_break_indented_markuped),
                    })
                elif question.question_type in ['simple_choice', 'multiple_choice']:
                    multiple_answers = input_line_index != 0
                    answer = str(input_line._get_answer_value())
                    # For picture answers without label, we use the filename by the way
                    if input_line.suggested_answer_id and not input_line._get_answer_value():
                        answer = input_line.suggested_answer_id.value_image_filename or ''
                    answers.append(Markup('%(separator)s %(answer)s') % {
                        'separator': ' —' if not multiple_answers else ',',  # The "else" is useful for multiple suggested answers
                        'answer': answer,
                    })

                elif question.question_type == 'text_box':
                    # Leave the placeholder values in the constructor to keep line break with indentation
                    answers = ['', Markup('%(text)s' % {'text': escape(input_line._get_answer_value()).replace('\n', line_break_indented_markuped)})]  # '' for line break after with the next join

            # Leave the placeholder values in the constructor so as not to escape the pretty print
            html_input_lines.append(Markup('<li>%(question_title)s%(initial_indent)s%(user_inputs)s</li>') % {
                'question_title': escape(question.title),
                'initial_indent': line_break_indented_markuped if initial_indent else '',
                'user_inputs': Markup('').join(answers) if multiple_answers else line_break_indented_markuped.join(answers),
            })

        # Leave the placeholder values in the constructor so as not to escape the pretty print
        description = Markup('<div>%(answers)s:</div><ul>%(survey_answers)s</ul>') % {
            'answers': _('Answers'),
            'survey_answers': Markup('').join(html_input_lines),
        }
        return {
            'description': description,
            'user_nickname': user_nickname,
            'public_user_mail': public_user_mail,
        }

    def action_redirect_lead(self):
        ''' Shows the lead associated, created from inputs '''
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('crm.crm_lead_opportunities')
        action['views'] = [((self.env.ref('crm.crm_lead_view_form').id), 'form')]
        action['res_id'] = self.lead_id.id
        return action
