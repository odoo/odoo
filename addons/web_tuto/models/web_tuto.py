import logging

from lxml import etree

from odoo import api, fields, models, modules, Command
from odoo.addons.web.controllers.utils import get_action
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

FIELD_XPATH = '//field[@name=$name][not(ancestor::field)]'
BUTTON_XPATH = '//button[@name=$name][not(ancestor::field)]'


class Tutorial(models.Model):
    """ A tutorial guides the users through an app, at their own pace and in
    their own order. It goes through views, its chapters, and in each of them
    through steps: fields to fill in and buttons to click, with their help.
    For instance, the tutorial of CRM:

    - chapter 1, the kanban view of the leads: new, partner_id,
      expected_revenue, priority, edit;
    - chapter 2, the form view of a lead: tag_ids, description, send,
      stage_id, delete (a hint, only shown).

    For each user, a step is done once they did it (see the client side,
    ``TutorialPlugin``), and the tutorial once the steps of its last chapter
    are done, or once they skip it or mark it as done. The tutorials run for
    the internal users who enabled them (by default on a trial database), one
    per module at a time (see ``_get_modules``).
    """
    _name = 'web_tuto.tutorial'
    _description = "Tutorial"
    _order = "sequence, name, id"

    name = fields.Char(required=True)
    title = fields.Char(translate=True, help="The name of the tutorial shown to the users")
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=1000)
    chapter_ids = fields.One2many("web_tuto.chapter", "tutorial_id", help="The views the tutorial goes through, in that order")
    rainbow_man_message = fields.Char(
        default=lambda self: self.env._("Good job! You went through all steps of this tutorial."), translate=True,
    )
    user_done_ids = fields.Many2many("res.users", help="The users who finished, skipped or marked as done the tutorial")

    _uniq_name = models.Constraint(
        'unique(name)',
        "A tutorial already exists with this name. Tutorial's name must be unique!",
    )

    def _get_running_domain(self):
        return [("user_done_ids", "not in", self.env.user.id), ("chapter_ids", "!=", False)]

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
        the steps already done by them, skipping the ones of which a view
        isn't accessible to them. A module runs one tutorial at a time: the
        first of them by sequence, the ones without module each running. """
        if not self._can_run():
            return []
        tutorials = []
        running_modules = set()
        candidates = self.search(self._get_running_domain())
        tutorial_modules = candidates._get_modules()
        for tutorial in candidates:
            module = tutorial_modules[tutorial.id]
            if module in running_modules:
                continue
            if not tutorial._is_accessible():
                continue
            try:
                tutorials.append(tutorial._get_tutorial_json())
            except ValidationError:
                _logger.exception("Invalid tutorial %s", tutorial.name)
                continue
            if module:
                running_modules.add(module)
        return tutorials

    @api.model
    def get_user_tutorials(self):
        """ Return the tutorials the current user can go through, whether
        tutorials are enabled for them or not, with their title prefixed by the
        name of their module if any, and their state for them: "new"
        if they didn't start it yet, "running" if they did, "done" if they
        finished or skipped it; and, for each of its chapters (its views),
        whether each of its steps is shown as done: the ones up to the last
        done one, all of them once the tutorial is done """
        if not self.env.user._is_internal():
            return []
        done_steps = self.env['web_tuto.step'].sudo().search([('user_done_ids', 'in', self.env.user.id)])
        done_step_ids = set(done_steps.ids)
        started_tutorials = done_steps.tutorial_id
        candidates = self.search([('chapter_ids', '!=', False)])
        tutorial_modules = candidates._get_modules()
        module_names = dict(self.env['ir.module.module'].sudo().search([
            ('name', 'in', list(tutorial_modules.values())),
        ]).mapped(lambda module: (module.name, module.shortdesc)))
        tutorials = []
        for tutorial in candidates:
            if not tutorial._is_accessible():
                continue
            if self.env.user in tutorial.sudo().user_done_ids:
                state = 'done'
            elif tutorial in started_tutorials:
                state = 'running'
            else:
                state = 'new'
            steps = [step for chapter in tutorial.chapter_ids for step in chapter.step_ids]
            if state == 'done':
                shown_done_count = len(steps)
            else:
                shown_done_count = max((index + 1 for index, step in enumerate(steps) if step.id in done_step_ids), default=0)
            shown_done = [index < shown_done_count for index in range(len(steps))]
            chapters = []
            for chapter in tutorial.chapter_ids:
                chapters.append(shown_done[:len(chapter.step_ids)])
                shown_done = shown_done[len(chapter.step_ids):]
            title = tutorial.title or tutorial.name
            if module_name := module_names.get(tutorial_modules[tutorial.id]):
                title = f"{module_name} - {title}"
            tutorials.append({'id': tutorial.id, 'title': title, 'state': state, 'chapters': chapters})
        return tutorials

    def _get_modules(self):
        """ Return the module of each tutorial, by id: the one of its external
        id, or an empty string if it has none. A module runs one of its
        tutorials at a time (see ``get_running_tutorials``), and its name
        prefixes their title for the users (see ``get_user_tutorials``). """
        return {tutorial_id: xmlid.partition('.')[0] for tutorial_id, xmlid in self.get_external_id().items()}

    def _is_accessible(self):
        """ Whether the current user can read the models of the views of the
        tutorial """
        self.ensure_one()
        return all(self.env[model].has_access('read') for model in self.chapter_ids.view_id.sudo().mapped('model'))

    def _get_tutorial_json(self):
        """ Resolve the tutorial: its chapters, describing the views it goes
        through and, as their steps, the fields and buttons used in each of
        them.

        :return: the tutorial as a dict with its chapters (see
            ``web_tuto.chapter._get_chapter_json``)
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
            'chapters': [chapter._get_chapter_json(done_steps) for chapter in self.chapter_ids],
        }

    def _get_user_progress(self):
        """ The progress of the current user in the tutorial, if any """
        self.ensure_one()
        return self.env['web_tuto.tutorial.user'].sudo().search([
            ('tutorial_id', '=', self.id), ('user_id', '=', self.env.user.id),
        ])

    def mark_done(self):
        """ End the tutorials for the current user: finished, skipped, or
        marked as done """
        if self.env.user._is_internal():
            self.sudo().user_done_ids = [Command.link(self.env.user.id)]

    def save_resume_url(self, url):
        """ Remember the URL of the current chapter of the tutorial for the
        current user, to resume it there """
        self.ensure_one()
        if not self.env.user._is_internal() or not isinstance(url, str) or not url.startswith('/') or url.startswith('//'):
            return
        if progress := self._get_user_progress():
            progress.resume_url = url
        else:
            progress.create({'tutorial_id': self.id, 'user_id': self.env.user.id, 'resume_url': url})

    def action_restart(self):
        """ Restart the tutorial from scratch for the current user, reloading
        the web client on its first view """
        self.ensure_one()
        user = self.env.user
        self.sudo().user_done_ids = [Command.unlink(user.id)]
        self.sudo().chapter_ids.step_ids.user_done_ids = [Command.unlink(user.id)]
        self._get_user_progress().unlink()
        return self.action_resume()

    def action_resume(self):
        """ Go on with the tutorial where the current user left it: at the URL
        of their current chapter, on a new record if the one it displayed was
        deleted, or reloading the web client on its first view """
        self.ensure_one()
        self.env.user.sudo().tutorial_enabled = True
        if url := self._get_user_progress()._get_resume_url():
            return {'type': 'ir.actions.act_url', 'url': url, 'target': 'self'}
        window_action, menu = self._get_first_view_action()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {'action_id': window_action.id, 'menu_id': menu.id},
        }

    def _get_first_view_action(self):
        """ Return the window action opening the first view of the tutorial,
        among the ones of the groups of the current user, preferably one
        referencing that view, with its menu if any """
        view = self.chapter_ids[:1].view_id.sudo()
        user_groups = self.env.user.all_group_ids
        window_actions = self.env['ir.actions.act_window'].sudo().search([('res_model', '=', view.model)]).filtered(
            lambda window_action: view.type in (window_action.view_mode or '').split(',')
            and (not window_action.group_ids or window_action.group_ids & user_groups),
        )
        referencing_actions = window_actions.filtered(
            lambda window_action: view in window_action.view_id | window_action.view_ids.view_id,
        )
        window_actions = referencing_actions + (window_actions - referencing_actions)
        for window_action in window_actions:
            menu = self.env['ir.ui.menu'].search([('action', '=', f'{window_action._name},{window_action.id}')], limit=1)
            if menu:
                return window_action, menu
        return window_actions[:1], self.env['ir.ui.menu']


class TutorialUser(models.Model):
    _name = 'web_tuto.tutorial.user'
    _description = "Tutorial Progress"

    tutorial_id = fields.Many2one("web_tuto.tutorial", required=True, index=True, ondelete="cascade")
    user_id = fields.Many2one("res.users", required=True, ondelete="cascade")
    resume_url = fields.Char()

    _uniq_tutorial_user = models.Constraint('unique(tutorial_id, user_id)', "A user has one progress by tutorial.")

    def _get_resume_url(self):
        """ The URL to resume the tutorial at: the saved one, unless one of its
        records doesn't exist anymore. The path of a URL of the web client is a
        sequence of actions, each one followed by the id of its record (or
        ``new``) if it displays one, e.g. ``/odoo/crm/12/action-42/7``. It is
        checked action by action: the URL stops at the action of the first
        record that doesn't exist anymore, on a new record of it if it's the
        last one. For instance, with the lead 12 deleted:

        - ``/odoo/crm/12`` resumes at ``/odoo/crm/new``;
        - ``/odoo/crm/12/action-42/7`` resumes at ``/odoo/crm``.

        :return: the URL, or False if there's none or one of its actions
            doesn't exist anymore
        """
        if not self.resume_url:
            return False
        prefix, _sep, path = self.resume_url.partition('?')[0].strip('/').partition('/')
        remaining = path.split('/') if path else []
        checked = []
        while remaining:
            action = get_action(self.env, remaining[0])
            if not action:
                return False
            checked.append(remaining.pop(0))
            if remaining and remaining[0] == 'new':
                checked.append(remaining.pop(0))
            elif remaining and remaining[0].isdigit():
                record_id = int(remaining.pop(0))
                model = action._fields.get('res_model') and action.res_model
                if model in self.env and not self.env[model].sudo().browse(record_id).exists():
                    return f"/{prefix}/{'/'.join(checked if remaining else [*checked, 'new'])}"
                checked.append(str(record_id))
        return self.resume_url


class Chapter(models.Model):
    _name = 'web_tuto.chapter'
    _description = "Tutorial's chapter"
    _order = "sequence, id"

    tutorial_id = fields.Many2one("web_tuto.tutorial", required=True, index=True, ondelete="cascade")
    sequence = fields.Integer()
    view_id = fields.Many2one("ir.ui.view", required=True, ondelete="cascade", help="The view the chapter is done in")
    step_ids = fields.One2many("web_tuto.step", "chapter_id", help="The fields and buttons used in the view")

    @api.depends("view_id.name")
    def _compute_display_name(self):
        for chapter in self:
            chapter.display_name = chapter.view_id.name

    def _get_chapter_json(self, done_steps):
        """ Resolve the chapter, with its steps.

        :param done_steps: the steps the current user already did
        :return: the chapter as a dict, with the type and the model of its
            view, and its steps as dicts with their ``type`` ("field" or
            "button") and the information the client needs to play them
        """
        self.ensure_one()
        view = self.view_id.sudo()
        archs = self._get_archs()
        steps = []
        for chapter_step in self.step_ids:
            step = chapter_step._resolve_step(archs)
            step.update(id=chapter_step.id, done=chapter_step in done_steps)
            steps.append(step)
        return {'id': self.id, 'view_type': view.type, 'model': view.model, 'steps': steps}

    def _get_archs(self):
        """ Return the archs in which the steps of the chapter are looked for,
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


class Step(models.Model):
    _name = 'web_tuto.step'
    _description = "Tutorial's step"
    _order = "sequence, id"

    chapter_id = fields.Many2one("web_tuto.chapter", required=True, index=True, ondelete="cascade")
    tutorial_id = fields.Many2one(related="chapter_id.tutorial_id", store=True, index=True)
    sequence = fields.Integer()
    type = fields.Selection(selection=[
        ("field", "Field"),
        ("button", "Button"),
    ], required=True, default="field")
    name = fields.Char(required=True, help="The field (a field of the lines of a x2many field being given as x2many_field.field) or the button of the view of the chapter: a button of the view, or a generic one (e.g. new)")
    content = fields.Char(required=True, translate=True)
    hint = fields.Boolean(help="Only show the step to the user, who goes on with the Next button")
    tooltip_position = fields.Selection(selection=[
        ("bottom", "Bottom"),
        ("top", "Top"),
        ("right", "Right"),
        ("left", "Left"),
    ], default="bottom")
    user_done_ids = fields.Many2many("res.users")

    @api.constrains("type", "chapter_id", "name")
    def _check_step(self):
        for step in self:
            step._resolve_step()

    def mark_done(self):
        if self.env.user._is_internal():
            self.sudo().user_done_ids = [Command.link(self.env.user.id)]

    def mark_undone(self):
        if self.env.user._is_internal():
            self.sudo().user_done_ids = [Command.unlink(self.env.user.id)]

    def _get_generic_buttons(self):
        """ Return the generic buttons a button step can use, which aren't
        buttons of its view, with the types of view they can be used in.
        Their element is given on the client by the registry
        ``web_tuto.buttons``, both being extended to add some. """
        return {
            'new': ('kanban', 'list', 'form'),
            'create': ('kanban',),
            'edit': ('kanban',),
            'send': ('form',),
            'log': ('form',),
            'delete': ('form',),
        }

    def _get_name(self):
        self.ensure_one()
        return self.get_external_id()[self.id] or f"#{self.id}"

    def _resolve_step(self, archs=None):
        """ Resolve the field or the button of a step in the view of its
        chapter: a field of the lines of a x2many field is given as
        ``x2many_field.field``, a button is a button of the view or a generic
        one (see ``_get_generic_buttons``).

        :return: the step as a dict with its ``type`` ("field" or "button")
            and the information the client needs to play it
        :raise ValidationError: if the view doesn't have it
        """
        self.ensure_one()
        view = self.chapter_id.view_id.sudo()
        view_name = view.xml_id or view.name
        archs = archs or self.chapter_id._get_archs()
        resolved = None
        if self.type == 'field':
            x2many, _dot, name = self.name.rpartition('.')
            names = [name, 'display_name'] if name == self.env[view.model]._rec_name else [name]
            for arch, scope in archs:
                if x2many:
                    resolved = self._resolve_subfield(arch, scope, x2many, name)
                else:
                    nodes = [node for field_name in names for node in arch.xpath(FIELD_XPATH, name=field_name)]
                    resolved = nodes and {'name': nodes[0].get('name'), 'scope': scope}
                if resolved:
                    break
            else:
                raise ValidationError(self.env._(
                    "Step %(step)s: '%(name)s' isn't a field of the view %(view)s.",
                    step=self._get_name(), name=self.name, view=view_name,
                ))
        else:
            scope = next((scope for arch, scope in archs if arch.xpath(BUTTON_XPATH, name=self.name)), None)
            generic_buttons = self._get_generic_buttons()
            if scope and self.name in generic_buttons:
                raise ValidationError(self.env._(
                    "Step %(step)s: '%(name)s' is both a button of the view %(view)s and a generic button.",
                    step=self._get_name(), name=self.name, view=view_name,
                ))
            if scope:
                resolved = {'name': self.name, 'scope': scope}
            elif self.name not in generic_buttons:
                raise ValidationError(self.env._(
                    "Step %(step)s: '%(name)s' is neither a button of the view %(view)s nor a generic button.",
                    step=self._get_name(), name=self.name, view=view_name,
                ))
            elif view.type not in generic_buttons[self.name]:
                raise ValidationError(self.env._(
                    "Step %(step)s: the button '%(button)s' can't be used in a %(view_type)s view.",
                    step=self._get_name(), button=self.name, view_type=view.type,
                ))
            else:
                resolved = {'name': self.name}
        return {
            **resolved,
            'type': self.type,
            'content': self.content,
            'hint': self.hint,
            'tooltip_position': self.tooltip_position,
        }

    def _resolve_subfield(self, arch, scope, parent_name, name):
        """ Resolve a field of the lines of a x2many field of the arch, as
        displayed by its subview

        :return: the step as a dict, or None if the arch doesn't display it
        """
        parent_nodes = arch.xpath(FIELD_XPATH, name=parent_name)
        if not parent_nodes:
            return None
        parent_node = parent_nodes[0]
        for node in parent_node.xpath('.//field[@name=$name]', name=name):
            if node.xpath('ancestor::field[1]')[0] is parent_node:
                return {'name': name, 'scope': scope, 'x2many': parent_name}
        return None
