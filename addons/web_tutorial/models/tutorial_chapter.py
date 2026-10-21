import ast

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class TutorialChapter(models.Model):
    """ A view of a tutorial, with its steps. A form chapter is shown in the
    forms of its model; a list or kanban chapter in any view of several records
    of its model; only with the values of its context, if any.
    """
    _name = 'web_tutorial.chapter'
    _description = "Tutorial Chapter"
    _order = "sequence, id"

    context = fields.Char(
        default="{}",
        help="The values of the context of its view, e.g. {'default_move_type': 'out_invoice'} for the form of a "
             "customer invoice, not to be shown in the views of the other records of its model (e.g. a vendor bill)",
    )
    model_id = fields.Many2one("ir.model", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    step_ids = fields.One2many("web_tutorial.step", "chapter_id", string="Steps")
    tutorial_id = fields.Many2one("web_tutorial.tutorial", required=True, index=True, ondelete="cascade")
    view_type = fields.Selection(
        [('form', "Form"), ('list', "List"), ('kanban', "Kanban")], required=True,
        help="A list or kanban chapter is shown in any view of several records of its model",
    )

    @api.constrains('context')
    def _check_context(self):
        for chapter in self:
            if not isinstance(chapter._get_context(), dict):
                raise ValidationError(self.env._("The context of a tutorial chapter must be a dictionary of values."))

    @api.constrains('model_id', 'view_type')
    def _check_steps(self):
        self.step_ids._check_name()

    def _get_context(self):
        self.ensure_one()
        try:
            return ast.literal_eval(self.context or "{}")
        except (SyntaxError, ValueError):
            return None

    def _get_chapter_json(self):
        """ Return the chapter for the client, with its steps """
        self.ensure_one()
        return {
            'context': self._get_context(),
            'id': self.id,
            'model': self.model_id.sudo().model,
            'steps': [step._get_step_json() for step in self.step_ids],
            'view_type': self.view_type,
        }
