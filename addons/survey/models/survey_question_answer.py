from textwrap import shorten

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SurveyQuestionAnswer(models.Model):
    """ A preconfigured answer for a question. This model stores values used
    for

      * simple choice, multiple choice: proposed values for the selection /
        radio;
      * matrix: row and column values;

    """
    _name = 'survey.question.answer'
    _rec_name = 'value'
    _rec_names_search = ['question_id.title', 'value']
    _order = 'question_id, sequence, id'
    _description = 'Survey Label'

    MAX_ANSWER_NAME_LENGTH = 90  # empirically tested in client dropdown

    # question and question related fields
    question_id = fields.Many2one('survey.question', string='Question', ondelete='cascade', index='btree_not_null')
    matrix_question_id = fields.Many2one('survey.question', string='Question (as matrix row)', ondelete='cascade', index='btree_not_null')
    question_type = fields.Selection(related='question_id.question_type')
    sequence = fields.Integer('Label Sequence order', default=10)
    scoring_type = fields.Selection(related='question_id.scoring_type')
    # answer related fields
    value = fields.Char('Suggested value', translate=True)
    value_image = fields.Image('Image', max_width=1024, max_height=1024)
    value_image_filename = fields.Char('Image Filename')
    value_label = fields.Char('Value Label', compute='_compute_value_label',
                              help="Answer label as either the value itself if not empty "
                                   "or a letter representing the index of the answer otherwise.")
    is_correct = fields.Boolean('Correct')
    answer_score = fields.Float('Score', help="A positive score indicates a correct choice; a negative or null score indicates a wrong answer")
    tag_ids = fields.Many2many('survey.question.answer.tag', string='Answer tags')

    _sql_constraints = [
        ('value_not_empty', "CHECK (value IS NOT NULL OR value_image_filename IS NOT NULL)",
         'Suggested answer value must not be empty (a text and/or an image must be provided).'),
    ]

    @api.depends('value_label', 'question_id.question_type', 'question_id.title', 'matrix_question_id')
    def _compute_display_name(self):
        """Render an answer name as "Question title : Answer label value", making sure it is not too long.

        Unless the answer is part of a matrix-type question, this implementation makes sure we have
        at least 30 characters for the question title, then we elide it, leaving the rest of the
        space for the answer.
        """
        for answer in self:
            answer_label = answer.value_label
            if not answer.question_id or answer.question_id.question_type == 'matrix':
                answer.display_name = answer_label
                continue
            title = answer.question_id.title or _("[Question Title]")
            n_extra_characters = len(title) + len(answer_label) + 3 - self.MAX_ANSWER_NAME_LENGTH  # 3 for `" : "`
            if n_extra_characters <= 0:
                answer.display_name = f'{title} : {answer_label}'
            else:
                answer.display_name = shorten(
                    f'{shorten(title, max(30, len(title) - n_extra_characters), placeholder="...")} : {answer_label}',
                    self.MAX_ANSWER_NAME_LENGTH,
                    placeholder="..."
                )

    @api.depends('question_id.suggested_answer_ids', 'sequence', 'value')
    def _compute_value_label(self):
        """ Compute the label as the value if not empty or a letter representing the index of the answer otherwise. """
        for answer in self:
            # using image -> use a letter to represent the value
            if not answer.value and answer.question_id and answer.id:
                answer_idx = answer.question_id.suggested_answer_ids.ids.index(answer.id)
                answer.value_label = chr(65 + answer_idx) if answer_idx < 27 else ''
            else:
                answer.value_label = answer.value or ''

    @api.constrains('question_id', 'matrix_question_id')
    def _check_question_not_empty(self):
        """Ensure that field question_id XOR field matrix_question_id is not null"""
        for label in self:
            if not bool(label.question_id) != bool(label.matrix_question_id):
                raise ValidationError(_("A label must be attached to only one question."))

    def _get_answer_matching_domain(self, row_id=False):
        self.ensure_one()
        if self.question_type == "matrix":
            return ['&', '&', ('question_id', '=', self.question_id.id), ('matrix_row_id', '=', row_id), ('suggested_answer_id', '=', self.id)]
        elif self.question_type in ('multiple_choice', 'simple_choice'):
            return ['&', ('question_id', '=', self.question_id.id), ('suggested_answer_id', '=', self.id)]
        return []
