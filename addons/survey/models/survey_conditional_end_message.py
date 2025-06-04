from random import randint
from odoo import fields, models


class SurveyConditionalEndMessage(models.Model):
    """ This is used to display an extra completion message depending on
        the most frequent type of response.
    """
    _name = 'survey.conditional.end.message'
    _description = 'Survey Conditional End Message'
    _order = 'sequence,id'

    name = fields.Char('Name', required=True, translate=True)
    sequence = fields.Integer(
        'Sequence', required=True, default=1,
        help='Determines which extra end message to display in the event of a strict tie between two or more messages.')
    body = fields.Html(
        'Body', translate=True,
        help="This message will be displayed when the survey is completed and is the most frequently associated with the participant's answers")
    survey_id = fields.Many2one('survey.survey', string='Survey', required=True, ondelete='cascade', index=True)
    survey_question_ids = fields.One2many(related='survey_id.question_ids')
    question_answer_ids = fields.Many2many('survey.question.answer', string='Question Answers')
    color = fields.Integer(string='Color Index', default=lambda __: randint(1, 11))
