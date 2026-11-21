from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.models import get_public_method

GENERIC_BUTTONS = ('New', 'Edit', 'Delete', 'Duplicate', 'Archive', 'Unarchive')


class TutorialStep(models.Model):
    """ A step of the view of its chapter, done by the user or with Next, its
    ``name`` depending on its type:

    - ``field``: a field of the view (e.g. ``partner_id``, or
      ``order_line.product_id`` for a field of the lines of a x2many field),
      done once focused; in a kanban view, a field of its quick create (or of
      the form, if opened without it);
    - ``method``: the method of the model called by a button of the view (e.g.
      ``action_post``), done once clicked;
    - ``server_action``: the xmlid of a server action bound to the model, done
      once run from the actions menu;
    - ``generic_button``: a button of the web client (``New``, ``Edit`` opening
      the form of a kanban quick create, ``Delete``, ``Duplicate``,
      ``Archive`` or ``Unarchive``), done once clicked.

    A hint is only shown, the user going on with Next.
    """
    _name = 'web_tutorial.step'
    _description = "Tutorial Step"
    _order = "sequence, id"

    chapter_id = fields.Many2one("web_tutorial.chapter", required=True, index=True, ondelete="cascade")
    content = fields.Char(required=True, translate=True, help="The help shown by the pointer")
    hint = fields.Boolean(help="Only show the step, the user going on with Next")
    name = fields.Char(
        required=True,
        help="Depending on its type: the field (e.g. partner_id, or order_line.product_id for a field of the lines "
             "of a x2many field), the method of the model (e.g. action_post), the xmlid of a server action bound to "
             "the model, or the generic button (New, Edit, Delete, Duplicate, Archive or Unarchive)",
    )
    sequence = fields.Integer(default=10)
    type = fields.Selection(
        [
            ('field', "Field"),
            ('method', "Method"),
            ('server_action', "Server Action"),
            ('generic_button', "Generic Button"),
        ],
        required=True,
    )

    @api.constrains('type', 'name', 'chapter_id')
    def _check_name(self):
        for step in self:
            model = self.env[step.chapter_id.model_id.sudo().model]
            if step.type == 'field':
                step._check_field(model)
            elif step.type == 'method':
                step._check_method(model)
            elif step.type == 'server_action':
                step._check_server_action(model)
            else:
                step._check_generic_button()

    def _check_field(self, model):
        if self.chapter_id.view_type == 'list':
            raise ValidationError(self.env._("The field step “%s” must be in a form or kanban chapter.", self.content))
        x2many, _dot, name = self.name.rpartition('.')
        field = model._fields.get(x2many or name)
        if x2many:
            field = field and field.type in ('one2many', 'many2many') and self.env[field.comodel_name]._fields.get(name)
        if not field:
            raise ValidationError(self.env._(
                "The field step “%(content)s” names %(field)s, which isn't a field of %(model)s, nor of the lines of "
                "one of its x2many fields.",
                content=self.content, field=self.name, model=model._name,
            ))

    def _check_generic_button(self):
        if self.name not in GENERIC_BUTTONS:
            raise ValidationError(self.env._(
                "The step “%(content)s” names %(name)s, which isn't a generic button (%(buttons)s).",
                content=self.content, name=self.name, buttons=", ".join(GENERIC_BUTTONS),
            ))
        if self.name == 'Edit' and self.chapter_id.view_type != 'kanban':
            raise ValidationError(self.env._(
                "The step “%s” clicks Edit, which only opens the form of the quick create of a kanban chapter.",
                self.content,
            ))

    def _check_method(self, model):
        try:
            get_public_method(model, self.name)
        except (AccessError, AttributeError):
            raise ValidationError(self.env._(
                "The step “%(content)s” calls %(method)s, which isn't a public method of %(model)s.",
                content=self.content, method=self.name, model=model._name,
            )) from None

    def _check_server_action(self, model):
        action = self._get_server_action()
        if not action or action.sudo().binding_model_id.model != model._name:
            raise ValidationError(self.env._(
                "The step “%(content)s” runs %(action)s, which isn't a server action bound to %(model)s.",
                content=self.content, action=self.name, model=model._name,
            ))

    def _get_server_action(self):
        self.ensure_one()
        action = self.env.ref(self.name, raise_if_not_found=False) if '.' in self.name else None
        return action if action and action._name == 'ir.actions.server' else None

    def _get_step_json(self):
        """ Return the step for the client, with the name a server action has
        in its actions menu """
        self.ensure_one()
        action = self.type == 'server_action' and self._get_server_action()
        return {
            'action_name': action.sudo().name if action else "",
            'content': self.content,
            'hint': self.hint,
            'id': self.id,
            'name': self.name,
            'type': self.type,
        }
