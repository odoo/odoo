from odoo import fields, models


class JobMatchAnswerWeight(models.Model):
    _name = 'job.match.answer.weight'
    _description = 'Job Match Answer Weight'
    _order = 'question_id, answer_id, profile_id'

    answer_id = fields.Many2one(
        'survey.question.answer', string='Answer',
        required=True, ondelete='cascade', index=True)
    profile_id = fields.Many2one(
        'job.match.profile', string='Job Profile',
        required=True, ondelete='cascade', index=True)
    points = fields.Integer(
        'Points', default=1,
        help="Points this answer grants to the job profile. May be negative. "
             "Ignored when 'Eliminates' is set.")
    is_eliminating = fields.Boolean(
        'Eliminates',
        help="If the participant picks this answer, the job profile is entirely "
             "excluded from the results, regardless of points. Use for hard "
             "requirements, e.g. a language the role requires.")
    # Convenience related fields for grouping and domain filtering.
    question_id = fields.Many2one(
        'survey.question', related='answer_id.question_id',
        store=True, string='Question')
    survey_id = fields.Many2one(
        'survey.survey', related='answer_id.question_id.survey_id',
        store=True, string='Survey')

    _answer_profile_uniq = models.Constraint(
        'unique(answer_id, profile_id)',
        'A job profile can only have one weight per answer.')
