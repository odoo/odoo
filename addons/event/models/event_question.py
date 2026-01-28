# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class EventQuestion(models.Model):
    _name = 'event.question'
    _rec_name = 'title'
    _order = 'sequence,id'
    _description = 'Event Question'

    title = fields.Char(required=True, translate=True)
    question_type = fields.Selection([
        ('simple_choice', 'Selection'),
        ('text_box', 'Text Input'),
        ('name', 'Name'),
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('company_name', 'Company'),
    ], default='simple_choice', string="Question Type", required=True)
    active = fields.Boolean('Active', default=True)
    event_type_ids = fields.Many2many('event.type', string='Event Types', copy=False)
    event_ids = fields.Many2many('event.event', string='Events', copy=False)
    event_count = fields.Integer('# Events', compute='_compute_event_count')
    is_default = fields.Boolean('Default question', help="Include by default in new events.")
    is_reusable = fields.Boolean('Is Reusable',
                                 compute='_compute_is_reusable', default=True, store=True,
                                 help='Allow this question to be selected and reused for any future event. Always true for default questions.')
    answer_ids = fields.One2many('event.question.answer', 'question_id', "Answers", copy=True)
    sequence = fields.Integer(default=10)
    once_per_order = fields.Boolean('Ask once per order',
                                    help="Check this for order-level questions (e.g., 'Company Name') where the answer is the same for everyone.")
    is_mandatory_answer = fields.Boolean('Mandatory Answer')

    _check_default_question_is_reusable = models.Constraint(
        'CHECK(is_default IS DISTINCT FROM TRUE OR is_reusable IS TRUE)',
        "A default question must be reusable."
    )

    @api.depends('event_ids')
    def _compute_event_count(self):
        event_count_per_question = dict(self.env['event.event']._read_group(
            domain=[('question_ids', 'in', self.ids)],
            groupby=['question_ids'],
            aggregates=['__count']
        ))
        for question in self:
            question.event_count = event_count_per_question.get(question, 0)

    @api.depends('is_default', 'event_type_ids')
    def _compute_is_reusable(self):
        self.filtered('is_default').is_reusable = True

    def write(self, vals):
        """ We add a check to prevent changing the question_type of a question that already has answers.
        Indeed, it would mess up the event.registration.answer (answer type not matching the question type). """

        if 'question_type' in vals:
            questions_new_type = self.filtered(lambda question: question.question_type != vals['question_type'])
            if questions_new_type:
                answer_count = self.env['event.registration.answer'].search_count([('question_id', 'in', questions_new_type.ids)])
                if answer_count > 0:
                    raise UserError(_("You cannot change the question type of a question that already has answers!"))
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_answered_question(self):
        if self.env['event.registration.answer'].search_count([('question_id', 'in', self.ids)]):
            raise UserError(_('You cannot delete a question that has already been answered by attendees. You can archive it instead.'))

    @api.ondelete(at_uninstall=False)
    def _unlink_except_default_question(self):
        if set(self.ids) & set(self.env['event.type']._default_question_ids()):
            raise UserError(_('You cannot delete a default question.'))

    def action_view_question_answers(self):
        """ Allow analyzing the attendees answers to event questions in a convenient way:

        - A graph view showing counts of each suggestion for simple_choice questions
          (Along with secondary pivot and list views)
        - A list view showing textual answers values for text_box questions.
        """
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("event.action_event_registration_report")
        action['context'] = {'search_default_question_id': self.id}
        if event_id := self.env.context.get('search_default_event_id'):
            action['context'].update(search_default_event_id=event_id)
        # Fetch attendee answers for which the event is still linked to the question.
        action['domain'] = [('event_id.question_ids', 'in', self.ids)]

        if self.question_type == 'simple_choice':
            action['views'] = [(False, 'graph'), (False, 'pivot'), (False, 'list')]
        elif self.question_type == 'text_box':
            action['views'] = [(False, 'list')]
        return action

    def action_event_view(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("event.action_event_view")
        action['domain'] = [('question_ids', 'in', self.ids)]
        return action
