import re

from odoo import api, fields, models, modules
from odoo.tools import SQL

WEB_CLIENT_URL = re.compile(r'/odoo(?:[/?#]|$)')
MAX_STEP_KEYS = 1000
MAX_STEP_KEY_LENGTH = 512
MAX_URL_LENGTH = 2048


class Tutorial(models.Model):
    """ A tutorial guides the users through an app at their own pace: it goes
    through views (its chapters), and in each of them through fields and
    actions (its steps), defined in the JS registry ``web_tutorial.tutorials``
    under its name. For instance, CRM: the kanban of the leads (New, name,
    partner_id, expected_revenue, priority, Edit), then the form of a lead
    (tag_ids, description, Send message, stage_id, Delete). It runs for the
    internal users who enabled the tutorials, one per module at a time.
    """
    _name = 'web_tutorial.tutorial'
    _description = "Tutorial"
    _order = "sequence, name, id"

    action_id = fields.Many2one(
        "ir.actions.act_window", required=True, ondelete="cascade",
        help="The action the tutorial starts from",
    )
    active = fields.Boolean(default=True)
    name = fields.Char(
        required=True,
        help="The technical name of the tutorial, its key in the JS registry web_tutorial.tutorials, e.g. crm_tutorial",
    )
    rainbow_man_message = fields.Char(
        default=lambda self: self.env._("Good job! You went through all steps of this tutorial."), translate=True,
    )
    sequence = fields.Integer(default=1000)
    title = fields.Char(translate=True, help="The name of the tutorial shown to the users")

    _uniq_name = models.Constraint(
        'unique(name)',
        "A tutorial already exists with this name. Tutorial's name must be unique!",
    )

    def action_restart(self):
        """ Restart the tutorial from scratch for the current user """
        self.ensure_one()
        self._get_user_progress().write({'done': False, 'done_steps': [], 'resume_url': False})
        return self.action_resume()

    def action_resume(self):
        """ Go on with the tutorial where the current user left it, otherwise
        from its action, enabling the tutorials for them """
        self.ensure_one()
        self.env.user.sudo().tutorial_enabled = True
        self._mark_played()
        if url := self._get_user_progress()._get_resume_url():
            return {'type': 'ir.actions.act_url', 'url': url, 'target': 'self'}
        menu = self.env['ir.ui.menu'].search([('action', '=', f'{self.action_id._name},{self.action_id.id}')], limit=1)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {'action_id': self.action_id.id, 'menu_id': menu.id},
        }

    @api.model
    def get_running_tutorials(self):
        """ Return the tutorials the current user didn't finish yet and can
        play, one per module: the one they played last, otherwise the first by
        sequence """
        if not self._can_run():
            return []
        tutorials = []
        running_modules = set()
        progresses = self._get_user_progresses()
        progress_by_tutorial = {progress.tutorial_id.id: progress for progress in progresses}
        unfinished = self.search([('id', 'not in', progresses.filtered('done').tutorial_id.ids)])
        played_progresses = progresses.filtered(
            lambda progress: progress.played_date and progress.tutorial_id in unfinished,
        ).sorted('played_date', reverse=True)
        played = played_progresses.tutorial_id.with_env(self.env)
        candidates = played + (unfinished - played)
        tutorial_modules = candidates._get_modules()
        for tutorial in candidates:
            module = tutorial_modules[tutorial.id]
            if module in running_modules or not tutorial._is_accessible():
                continue
            tutorials.append(tutorial._get_tutorial_json(progress_by_tutorial.get(tutorial.id, progresses.browse())))
            if module:
                running_modules.add(module)
        return tutorials

    @api.model
    def get_user_tutorials(self):
        """ Return the tutorials the current user can play, for their list of
        tutorials, with their ``state`` ("new", "running" or "done") and the
        keys of their ``done_steps`` """
        if not self.env.user._is_internal():
            return []
        progresses = self._get_user_progresses()
        progress_by_tutorial = {progress.tutorial_id.id: progress for progress in progresses}
        no_progress = progresses.browse()
        candidates = self.search([])
        tutorial_modules = candidates._get_modules()
        module_names = dict(self.env['ir.module.module'].sudo().search([
            ('name', 'in', list(tutorial_modules.values())),
        ]).mapped(lambda module: (module.name, module.shortdesc)))
        tutorials = []
        for tutorial in candidates:
            if not tutorial._is_accessible():
                continue
            progress = progress_by_tutorial.get(tutorial.id, no_progress)
            state = 'done' if progress.done else 'running' if progress.done_steps else 'new'
            title = tutorial.title or tutorial.name
            if module_name := module_names.get(tutorial_modules[tutorial.id]):
                title = f"{module_name} - {title}"
            tutorials.append({
                'done_steps': progress.done_steps or [],
                'id': tutorial.id,
                'name': tutorial.name,
                'state': state,
                'title': title,
            })
        return tutorials

    def mark_done(self):
        """ End the tutorials the current user can play: finished, skipped,
        or marked as done """
        if self.env.user._is_internal():
            for tutorial in self.filtered(lambda tutorial: tutorial._is_accessible()):
                tutorial._ensure_user_progress().done = True

    def mark_steps_done(self, keys):
        """ Mark the steps of the tutorial as done by the current user

        :param keys: the keys of the steps (see ``getStepKeys`` in JS)
        """
        self.ensure_one()
        if self.env.user._is_internal() and self._are_step_keys(keys):
            progress = self._ensure_user_progress()
            done_steps = progress.done_steps or []
            progress.done_steps = done_steps + [key for key in keys if key not in done_steps]

    def mark_steps_undone(self, keys):
        """ Mark the steps of the tutorial as not done by the current user

        :param keys: the keys of the steps (see ``getStepKeys`` in JS)
        """
        self.ensure_one()
        if self.env.user._is_internal() and self._are_step_keys(keys):
            progress = self._ensure_user_progress()
            progress.done_steps = [key for key in progress.done_steps or [] if key not in keys]

    def save_resume_url(self, url):
        """ Remember where to resume the tutorial: a URL of the web client """
        self.ensure_one()
        if (
            not self.env.user._is_internal() or not isinstance(url, str)
            or len(url) > MAX_URL_LENGTH or not WEB_CLIENT_URL.match(url)
        ):
            return
        self._ensure_user_progress().resume_url = url

    @api.model
    def _are_step_keys(self, keys):
        """ Whether the keys sent by the client are a bounded list of bounded
        strings (they can't be checked: the steps are only known by the client)
        """
        return (
            isinstance(keys, list) and len(keys) <= MAX_STEP_KEYS
            and all(isinstance(key, str) and len(key) <= MAX_STEP_KEY_LENGTH for key in keys)
        )

    def _can_run(self):
        """ Whether tutorials run for the current user, never during the tests
        (not to interfere with their tours) """
        user = self.env.user
        return bool(user and user.tutorial_enabled and user._is_internal() and not modules.module.current_test)

    def _ensure_user_progress(self):
        """ The progress of the current user in the tutorial, created if they
        have none yet: an upsert, for the steps done in a row (sent in
        concurrent requests) not to create it twice, which would fail on its
        unique constraint instead of being retried as a serialization failure
        """
        self.ensure_one()
        if progress := self._get_user_progress():
            return progress
        self.env.execute_query(SQL("""
            INSERT INTO web_tutorial_tutorial_user (tutorial_id, user_id, create_uid, write_uid, create_date, write_date)
            VALUES (%(tutorial_id)s, %(user_id)s, %(user_id)s, %(user_id)s, NOW() AT TIME ZONE 'UTC', NOW() AT TIME ZONE 'UTC')
            ON CONFLICT (tutorial_id, user_id) DO NOTHING
        """, tutorial_id=self.id, user_id=self.env.user.id))
        return self._get_user_progress()

    def _get_modules(self):
        """ Return the module of each tutorial by id, from its external id
        (an empty string if none) """
        return {tutorial_id: xmlid.partition('.')[0] for tutorial_id, xmlid in self.get_external_id().items()}

    def _get_tutorial_json(self, progress):
        """ Return the tutorial for the client, which must be accessible to
        the current user, with their progress in it (if any) """
        self.ensure_one()
        return {
            'done_steps': progress.done_steps or [],
            'id': self.id,
            'name': self.name,
            'rainbow_man_message': self.rainbow_man_message,
        }

    def _get_user_progress(self):
        """ The progress of the current user in the tutorial, if any """
        self.ensure_one()
        return self.env['web_tutorial.tutorial.user'].sudo().search([
            ('tutorial_id', '=', self.id), ('user_id', '=', self.env.user.id),
        ])

    @api.model
    def _get_user_progresses(self):
        """ The progress of the current user in each tutorial they started """
        return self.env['web_tutorial.tutorial.user'].sudo().search([('user_id', '=', self.env.user.id)])

    def _is_accessible(self):
        """ Whether the current user can open the action of the tutorial: its
        groups, if any, and reading its model """
        self.ensure_one()
        action = self.action_id.sudo()
        if action.group_ids and not action.group_ids & self.env.user.all_group_ids:
            return False
        return action.res_model in self.env and self.env[action.res_model].has_access('read')

    def _mark_played(self):
        """ Run the tutorial first among the ones of its module """
        self._ensure_user_progress().played_date = fields.Datetime.now()
