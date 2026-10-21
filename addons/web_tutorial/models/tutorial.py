from odoo import api, fields, models, modules
from odoo.exceptions import AccessError
from odoo.fields import Command


class Tutorial(models.Model):
    """ A tutorial guides the users through an app at their own pace: it goes
    through views (its chapters), and in each of them through fields and
    buttons (its steps). For instance, Sales: the form of a quotation
    (partner_id, order_line, order_line.label, ..., action_quotation_send),
    opened with the New button of the list of the quotations. It runs for the
    internal users who started it (on a trial database, for all of them), one
    per module at a time.
    """
    _name = 'web_tutorial.tutorial'
    _description = "Tutorial"
    _order = "sequence, name, id"

    action_id = fields.Many2one(
        "ir.actions.act_window", required=True, ondelete="cascade",
        help="The action the tutorial starts from",
    )
    active = fields.Boolean(default=True)
    always_show_tooltip = fields.Boolean(help="Show the tooltip of each step without hovering the pointer")
    chapter_ids = fields.One2many("web_tutorial.chapter", "tutorial_id", string="Chapters")
    group_ids = fields.Many2many(
        "res.groups", string="Groups",
        help="The users the tutorial is for (e.g. the ones who can create its records), if not anyone who can open "
             "its action",
    )
    name = fields.Char(required=True, help="The technical name of the tutorial, e.g. crm_tutorial")
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
        """ Play the tutorial from scratch for the current user, from its
        action """
        self.ensure_one()
        self._check_accessible()
        self._ensure_user_progress().write({
            'done': False, 'done_step_ids': [Command.clear()], 'played_date': fields.Datetime.now(),
        })
        menu = self.env['ir.ui.menu'].search([('action', '=', f'{self.action_id._name},{self.action_id.id}')], limit=1)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {'action_id': self.action_id.id, 'menu_id': menu.id},
        }

    @api.model
    def get_running_tutorials(self):
        """ Return the tutorials the current user started and didn't finish
        yet, and can play, one per module: the one they started last; on a
        trial database, also the ones they didn't start, the first by sequence
        """
        if not self._can_run():
            return []
        tutorials = []
        running_modules = set()
        progresses = self._get_user_progresses()
        progress_by_tutorial = {progress.tutorial_id.id: progress for progress in progresses}
        played_progresses = progresses.filtered(
            lambda progress: progress.played_date and not progress.done,
        ).sorted('played_date', reverse=True)
        candidates = played_progresses.tutorial_id.with_env(self.env).filtered('active')
        if self.env['ir.config_parameter'].sudo().get_str('database.expiration_reason') == 'trial':
            candidates += self.search([('id', 'not in', progresses.filtered('done').tutorial_id.ids)]) - candidates
        tutorial_modules = candidates._get_modules()
        for tutorial in candidates:
            module = tutorial_modules[tutorial.id]
            if module in running_modules or not tutorial._is_accessible():
                continue
            tutorials.append(tutorial._get_tutorial_json(progress_by_tutorial.get(tutorial.id, progresses.browse())))
            if module:
                running_modules.add(module)
        return tutorials

    def mark_done(self):
        """ End the tutorials the current user can play: finished or skipped """
        if self.env.user._is_internal():
            for tutorial in self.filtered(lambda tutorial: tutorial._is_accessible()):
                tutorial._ensure_user_progress().done = True

    def mark_steps_done(self, step_ids):
        """ Mark the steps of the tutorial as done by the current user

        :param step_ids: the ids of steps of the tutorial
        """
        self.ensure_one()
        if self.env.user._is_internal() and self._is_accessible() and (steps := self._get_steps(step_ids)):
            self._ensure_user_progress().done_step_ids = [Command.link(step.id) for step in steps]

    def mark_steps_undone(self, step_ids):
        """ Mark the steps of the tutorial as not done by the current user

        :param step_ids: the ids of steps of the tutorial
        """
        self.ensure_one()
        if self.env.user._is_internal() and self._is_accessible() and (steps := self._get_steps(step_ids)):
            self._ensure_user_progress().done_step_ids = [Command.unlink(step.id) for step in steps]

    def _can_run(self):
        """ Whether tutorials run for the current user, never during the tests
        (not to interfere with their tours) """
        user = self.env.user
        return bool(user and user._is_internal() and not modules.module.current_test)

    def _check_accessible(self):
        """ Raise if the current user can't play the tutorial """
        if not self._is_accessible():
            raise AccessError(self.env._("You can't play the tutorial “%s”.", self.title or self.name))

    def _ensure_user_progress(self):
        """ The progress of the current user in the tutorial, created if they
        have none yet """
        self.ensure_one()
        return self._get_user_progress() or self.env['web_tutorial.tutorial.user'].sudo().create({
            'tutorial_id': self.id, 'user_id': self.env.user.id,
        })

    def _get_modules(self):
        """ Return the module of each tutorial by id, from its external id
        (an empty string if none) """
        return {tutorial_id: xmlid.partition('.')[0] for tutorial_id, xmlid in self.get_external_id().items()}

    def _get_steps(self, step_ids):
        """ The steps of the tutorial among the ids sent by the client """
        self.ensure_one()
        if not isinstance(step_ids, list):
            return self.env['web_tutorial.step']
        return self.chapter_ids.step_ids.filtered(lambda step: step.id in step_ids)

    def _get_tutorial_json(self, progress):
        """ Return the tutorial for the client, which must be accessible to
        the current user, with its chapters and their progress in it (if any)
        """
        self.ensure_one()
        return {
            'always_show_tooltip': self.always_show_tooltip,
            'chapters': [chapter._get_chapter_json() for chapter in self.chapter_ids],
            'done_steps': progress.done_step_ids.ids,
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
        """ Whether the current user can play the tutorial: they are in its
        groups, if any, and can open its action (its groups, if any, and
        reading its model) """
        self.ensure_one()
        if self.group_ids and not self.group_ids & self.env.user.all_group_ids:
            return False
        action = self.action_id.sudo()
        if action.group_ids and not action.group_ids & self.env.user.all_group_ids:
            return False
        return action.res_model in self.env and self.env[action.res_model].has_access('read')
