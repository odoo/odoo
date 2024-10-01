from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SurveyQuestionAnswerTag(models.Model):
    """ A tag associated  with a pre-configured response.
    This is used to evaluate the most frequent type of response from a participant,
    and to display a different completion message depending on the most frequent type of response.
    """
    _name = 'survey.question.answer.tag'
    _description = 'Survey Label Tag'
    _order = 'sequence,id'

    name = fields.Char('Tag', required=True, translate=True)
    sequence = fields.Integer('Sequence', required=True, default=1, help='Tag order also determines which end message to display in the event of a strict tie between two tags.')
    end_message = fields.Html('Message', translate=True,
        help="This message will be displayed when the survey is completed and this tag is the most frequently associated with the participant's answers")
    survey_id = fields.Many2one('survey.survey', string='Survey', required=True, ondelete='cascade')
    question_answer_ids = fields.Many2many('survey.question.answer', string='Question Answers')

    @api.onchange('sequence')
    def _onchange_sequence(self):
        for tag in self:
            if tag.sequence < 1:
                raise ValidationError(_("The tag sequence shall be greater than zero."))
