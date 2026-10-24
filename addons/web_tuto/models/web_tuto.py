import logging

from lxml import etree

from odoo import api, fields, models, modules, Command
from odoo.exceptions import ValidationError

# Verbs of the action steps, with the view types they can be used in
VERBS = {
    'new': ('kanban', 'list', 'form'),
    'add_stage': ('kanban',),
    'edit': ('kanban',),
    'send': ('form',),
    'log': ('form',),
    'delete': ('form',),
}

_logger = logging.getLogger(__name__)


class Tutorial(models.Model):
    _name = 'web_tuto.tutorial'
    _description = "Tutorial"
    _order = "sequence, name, id"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=1000)
    step_ids = fields.One2many("web_tuto.step", "tutorial_id", domain=[("parent_id", "=", False)])
    rainbow_man_message = fields.Char(
        default=lambda self: self.env._("Good job! You went through all steps of this tutorial."), translate=True,
    )
    user_consumed_ids = fields.Many2many("res.users")

    _uniq_name = models.Constraint(
        'unique(name)',
        "A tutorial already exists with this name. Tutorial's name must be unique!",
    )

    def _get_running_domain(self):
        return [("user_consumed_ids", "not in", self.env.user.id), ("step_ids", "!=", False)]

    def _can_run(self):
        """ The tutorials don't run during the tests, not to interfere with
        their tours """
        user = self.env.user
        return bool(user and user.tutorial_enabled and user._is_internal() and not modules.module.current_test)

    @api.model
    def has_running_tutorials(self):
        return self._can_run() and bool(self.search_count(self._get_running_domain(), limit=1))

    @api.model
    def get_running_tutorials(self):
        """ Return the tutorials the current user didn't go through yet, with
        the actions already done by them, skipping the ones of which a view
        isn't accessible to them """
        if not self._can_run():
            return []
        tutorials = []
        for tutorial in self.search(self._get_running_domain()):
            if not all(self.env[model].has_access('read') for model in tutorial.step_ids.view_id.sudo().mapped('model')):
                continue
            try:
                tutorials.append(tutorial._get_tutorial_json())
            except ValidationError:
                _logger.exception("Invalid tutorial %s", tutorial.name)
        return tutorials

    def _get_tutorial_json(self):
        """ Resolve the tutorial: its steps describing the views it goes through
        and, as their child steps, the actions done in each of them.

        :return: the tutorial as a dict with, for each view, its actions as
            dicts with a ``kind`` key ("field", "button" or "verb") and the
            information the client needs to play it
        :raise ValidationError: if a step doesn't match its view
        """
        self.ensure_one()
        done_steps = self.env['web_tuto.step'].search([
            ('tutorial_id', '=', self.id), ('user_done_ids', 'in', self.env.user.id),
        ])
        return {
            'id': self.id,
            'name': self.name,
            'rainbowManMessage': self.rainbow_man_message,
            'views': [view_step._get_view_json(done_steps) for view_step in self.step_ids],
        }

    def consume(self):
        if self.env.user._is_internal():
            self.sudo().user_consumed_ids = [Command.link(self.env.user.id)]

    def action_restart(self):
        """ Restart the tutorial from scratch for the current user, reloading
        the web client on its first view """
        self.ensure_one()
        user = self.env.user
        self.sudo().user_consumed_ids = [Command.unlink(user.id)]
        self.sudo().step_ids.child_ids.user_done_ids = [Command.unlink(user.id)]
        user.sudo().tutorial_enabled = True
        window_action, menu = self._get_first_view_action()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {'action_id': window_action.id, 'menu_id': menu.id},
        }

    def _get_first_view_action(self):
        """ Return the window action opening the first view of the tutorial,
        preferably one referencing that view, with its menu if any """
        view = self.step_ids[:1].view_id.sudo()
        window_actions = self.env['ir.actions.act_window'].search([('res_model', '=', view.model)]).filtered(
            lambda window_action: view.type in (window_action.view_mode or '').split(','),
        ).sorted(lambda window_action: view not in window_action.view_id | window_action.view_ids.view_id)
        for window_action in window_actions:
            menu = self.env['ir.ui.menu'].search([('action', '=', f'{window_action._name},{window_action.id}')], limit=1)
            if menu:
                return window_action, menu
        return window_actions[:1], self.env['ir.ui.menu']


class Step(models.Model):
    _name = 'web_tuto.step'
    _description = "Tutorial's step"
    _order = "sequence, id"
    _rec_name = "action"

    tutorial_id = fields.Many2one(
        "web_tuto.tutorial", required=True, index=True, ondelete="cascade",
        compute="_compute_tutorial_id", store=True, readonly=False, precompute=True,
    )
    sequence = fields.Integer()
    # a step with a view, whose child steps are the actions done in it
    parent_id = fields.Many2one("web_tuto.step", index=True, ondelete="cascade")
    child_ids = fields.One2many("web_tuto.step", "parent_id")
    view_id = fields.Many2one("ir.ui.view", ondelete="cascade")
    action = fields.Char(help="Field or button of the view of the parent step, or one of the verbs: " + ", ".join(VERBS))
    content = fields.Char(translate=True)
    hint = fields.Boolean(help="Only show the action to the user, who goes on with the Next button")
    tooltip_position = fields.Selection(selection=[
        ("bottom", "Bottom"),
        ("top", "Top"),
        ("right", "Right"),
        ("left", "Left"),
    ], default="bottom")
    user_done_ids = fields.Many2many("res.users")

    @api.depends("action", "view_id.name")
    def _compute_display_name(self):
        for step in self:
            step.display_name = step.action or step.view_id.name

    @api.depends("parent_id")
    def _compute_tutorial_id(self):
        for step in self:
            step.tutorial_id = step.parent_id.tutorial_id or step.tutorial_id

    @api.constrains("parent_id", "view_id", "action")
    def _check_step(self):
        for step in self:
            if step.parent_id:
                if step.view_id or not step.action or not step.parent_id.view_id:
                    raise ValidationError(self.env._(
                        "The step %s must have an action, and a step with a view as parent.", step._get_name(),
                    ))
                step._resolve_action()
            elif not step.view_id or step.action:
                raise ValidationError(self.env._(
                    "The step %s without parent must have a view, and no action.", step._get_name(),
                ))

    def mark_done(self):
        if self.env.user._is_internal():
            self.sudo().user_done_ids = [Command.link(self.env.user.id)]

    def mark_undone(self):
        if self.env.user._is_internal():
            self.sudo().user_done_ids = [Command.unlink(self.env.user.id)]

    def _get_name(self):
        self.ensure_one()
        return self.get_external_id()[self.id] or f"#{self.id}"

    def _get_view_json(self, done_steps):
        self.ensure_one()
        view = self.view_id.sudo()
        archs = self._get_archs()
        actions = []
        stage_count = 0
        for action_step in self.child_ids:
            action = action_step._resolve_action(archs)
            if action['kind'] == 'verb' and action['verb'] == 'add_stage':
                stage_count += 1
                action['stage_name'] = f"Stage {stage_count}"
            action.update(id=action_step.id, done=action_step in done_steps)
            actions.append(action)
        return {'id': self.id, 'type': view.type, 'model': view.model, 'xmlid': view.xml_id, 'actions': actions}

    def _get_archs(self):
        """ Return the archs in which the actions of a view step are looked for,
        in that order, as a list of ``(arch, scope)``: the quick create form of
        a kanban view (where its fields are edited), the view and its primary
        extensions (e.g. the same form with a footer, opened in a dialog) """
        self.ensure_one()
        view = self.view_id.sudo()
        Model = self.env[view.model]
        archs = []
        primary_views = self.env['ir.ui.view'].sudo().search([('inherit_id', '=', view.id), ('mode', '=', 'primary')])
        for arch_view in view + primary_views:
            arch = Model.get_views([(arch_view.id, view.type)])['views'][view.type]['arch']
            archs.append((etree.fromstring(arch), f'.o_{view.type}_view'))
        quick_create_xmlid = archs[0][0].get('quick_create_view')
        if view.type == 'kanban' and quick_create_xmlid:
            quick_create_view = self.env.ref(quick_create_xmlid)
            quick_create_arch = Model.get_views([(quick_create_view.id, 'form')])['views']['form']['arch']
            archs.insert(0, (etree.fromstring(quick_create_arch), '.o_kanban_quick_create'))
        return archs

    def _resolve_action(self, archs=None):
        """ Resolve the action of an action step as a field, a button or a verb
        of the view of its parent step.

        :return: the action as a dict with a ``kind`` key ("field", "button" or
            "verb") and the information the client needs to play it
        """
        self.ensure_one()
        view = self.parent_id.view_id.sudo()
        archs = archs or self.parent_id._get_archs()
        Model = self.env[view.model]
        token = self.action
        names = [token]
        if token == Model._rec_name:
            names.append('display_name')
        resolved = None
        for arch, scope in archs:
            for name in names:
                field_nodes = arch.xpath('//field[@name=$name][not(ancestor::field)]', name=name)
                if field_nodes:
                    resolved = self._resolve_field(Model, field_nodes[0], scope)
                    break
            if resolved:
                break
            button_nodes = arch.xpath('//button[@name=$name][not(ancestor::field)]', name=token)
            if button_nodes:
                resolved = {
                    'kind': 'button', 'name': token, 'scope': scope,
                    'label': button_nodes[0].get('string') or ''.join(button_nodes[0].itertext()).strip(),
                }
                break
        if not resolved and token in VERBS:
            if view.type not in VERBS[token]:
                raise ValidationError(self.env._(
                    "Step %(step)s: '%(action)s' can't be used in a %(view_type)s view.",
                    step=self._get_name(), action=token, view_type=view.type,
                ))
            resolved = {'kind': 'verb', 'verb': token, 'view_type': view.type}
            if token == 'new' and view.type == 'kanban':
                kanban_arch = next(arch for arch, scope in archs if scope == '.o_kanban_view')
                resolved['quick_create'] = kanban_arch.get('on_create') == 'quick_create'
        if not resolved:
            raise ValidationError(self.env._(
                "Step %(step)s: '%(action)s' is neither a field nor a button of the view %(view)s, nor a verb.",
                step=self._get_name(), action=token, view=view.xml_id or view.name,
            ))
        resolved.update(
            content=self.content or '', label=resolved.get('label', ''),
            hint=self.hint, tooltip_position=self.tooltip_position,
        )
        return resolved

    def _resolve_field(self, Model, node, scope):
        name = node.get('name')
        return {
            'kind': 'field', 'name': name, 'scope': scope,
            'label': node.get('string') or Model._fields[name].string,
        }
