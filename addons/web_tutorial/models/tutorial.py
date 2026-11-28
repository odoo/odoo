from odoo import api, fields, models, modules
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Command


class Tutorial(models.Model):
    """ A tutorial guides the users through an app at their own pace: it goes
    through fields and buttons (its steps) of some views, the successive steps
    of a view making a chapter. For instance, Sales: the New button of the list
    of the quotations, then the form of a quotation (partner_id, order_line,
    order_line.label, ..., action_quotation_send). It runs for the
    internal users who started it (on a trial database, for all of them), one
    per module at a time.
    """
    _name = 'web_tutorial.tutorial'
    _description = "Tutorial"
    _order = "sequence, title, id"
    _rec_name = 'title'

    active = fields.Boolean(default=True)
    key = fields.Char(
        copy=False,
        help="Starts the tutorial from a link with ?tutorial=<key>; the xmlid of a tutorial defined in data",
    )
    end_message = fields.Text(
        default=lambda self: self.env._("Good job! You went through all steps of this tutorial."), translate=True,
    )
    expand_messages = fields.Boolean(
        help="Whether the tooltips of the steps are always open, without the pointer, for everyone",
    )
    group_ids = fields.Many2many("res.groups", string="Groups")
    sequence = fields.Integer(default=1000)
    step_ids = fields.One2many("web_tutorial.step", "tutorial_id", string="Steps", copy=True)
    title = fields.Char(required=True, translate=True)

    _key_uniq = models.Constraint('unique(key)', "A tutorial is started from a link by its key, unique.")

    def action_restart(self):
        """ Play the tutorial from scratch for the current user, from its
        starting action """
        self.ensure_one()
        self._check_accessible()
        self._ensure_user_progress().write({
            'done': False, 'done_step_ids': [Command.clear()], 'played_date': fields.Datetime.now(),
        })
        return self._get_start_action()

    @api.model
    def start_from_key(self, key, expand_messages=False):
        """ Play the tutorial of the key (from a link with ?tutorial=<key>)
        for the current user: going on from their progress, from scratch once
        finished or skipped; with the tooltips of its steps open for them if
        asked (?expand_messages=1)

        :return: the action starting it in the web client (see
            ``_get_start_action``); none if the user can't play it, or no
            tutorial has the key
        """
        if not key or not self.env.user._is_internal():
            return False
        tutorial = self.search([('key', '=', key)], limit=1)
        if not tutorial or not tutorial._is_accessible():
            return False
        progress = tutorial._ensure_user_progress()
        values = {'expand_messages': bool(expand_messages), 'played_date': fields.Datetime.now()}
        if progress.done:
            values.update(done=False, done_step_ids=[Command.clear()])
        progress.write(values)
        return tutorial._get_start_action()

    @api.model
    def _load_records(self, data_list, update=False):
        """ Give the tutorials defined in data their xmlid as key, by default """
        for data in data_list:
            if data.get('xml_id'):
                data['values'].setdefault('key', data['xml_id'])
        return super()._load_records(data_list, update)

    @api.model
    def get_running_tutorials(self):
        """ Return the tutorials the current user can play, one per module
        (each of the ones made in the UI, without module): the one they
        started last among the ones they didn't finish; on a trial database,
        all the modules' ones they didn't finish, started or not, the first
        by sequence for a module without a started one """
        if not self._can_run():
            return []
        tutorials = []
        running_modules = set()
        progresses = self._get_user_progresses()
        progress_by_tutorial = {progress.tutorial_id.id: progress for progress in progresses}
        candidates = self._get_started_tutorials(progresses)
        if self.env['ir.config_parameter'].sudo().get_str('database.expiration_reason') == 'trial':
            finished_tutorials = progresses.filtered('done').tutorial_id
            candidates |= self.search([('id', 'not in', finished_tutorials.ids)])
        tutorial_modules = candidates._get_modules()
        for tutorial in candidates:
            module = tutorial_modules[tutorial.id]
            if module in running_modules or not tutorial._is_accessible():
                continue
            tutorials.append(tutorial._get_tutorial_data(progress_by_tutorial.get(tutorial.id, progresses.browse())))
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
            raise AccessError(self.env._("You can't play the tutorial “%s”.", self.title))

    @api.constrains('step_ids')
    def _check_starting_action(self):
        for tutorial in self:
            if tutorial.step_ids and not tutorial.step_ids[0].action_id:
                raise ValidationError(self.env._(
                    "The first step of the tutorial “%s” needs an action, the tutorial starting from it.",
                    tutorial.title,
                ))

    def _ensure_user_progress(self):
        """ The progress of the current user in the tutorial, created if they
        have none yet """
        self.ensure_one()
        return self._get_user_progress() or self.env['web_tutorial.progress'].create({
            'tutorial_id': self.id, 'user_id': self.env.user.id,
        })

    def _get_modules(self):
        """ Return the module of each tutorial by id, from its external id
        (an empty string if none) """
        return {tutorial_id: xmlid.partition('.')[0] for tutorial_id, xmlid in self.get_external_id().items()}

    @api.model
    def _get_started_tutorials(self, progresses):
        """ The tutorials the current user started and didn't finish, from the
        last started, but the archived ones

        :param progresses: the progresses of the user (see
            ``_get_user_progresses``)
        """
        started_progresses = progresses.filtered(lambda progress: progress.played_date and not progress.done)
        started_tutorials = started_progresses.sorted('played_date', reverse=True).tutorial_id
        return started_tutorials.filtered('active')

    def _get_starting_action(self):
        """ The action the tutorial starts from: the one of its first step """
        self.ensure_one()
        return self.step_ids[:1].action_id

    def _get_start_action(self):
        """ The action starting the tutorial in the web client, without
        reloading it: running the tutorials of the current user (among which
        it is), then opening its starting action in the app of its menu """
        action = self._get_starting_action()
        menu = self.env['ir.ui.menu'].search([('action', '=', f'{action._name},{action.id}')], limit=1)
        return {
            'type': 'ir.actions.client',
            'tag': 'web_tutorial.start',
            'params': {
                'action_id': action.id,
                'menu_id': menu.id,
                'running_tutorials': self.get_running_tutorials(),
            },
        }

    def _get_steps(self, step_ids):
        """ The steps of the tutorial among the ids sent by the client """
        self.ensure_one()
        if not isinstance(step_ids, list):
            return self.env['web_tutorial.step']
        return self.step_ids.filtered(lambda step: step.id in step_ids)

    def _get_tutorial_data(self, progress):
        """ Return the tutorial for the client, which must be accessible to
        the current user, with its steps and their progress in it (if any)
        """
        self.ensure_one()
        return {
            'expand_messages': self.expand_messages,
            'user_expand_messages': progress.expand_messages,
            'steps': [step._get_step_data() for step in self.step_ids],
            'done_steps': progress.done_step_ids.ids,
            'id': self.id,
            'title': self.title,
            'end_message': self.end_message,
        }

    def _get_user_progress(self):
        """ The progress of the current user in the tutorial, if any """
        self.ensure_one()
        return self.env['web_tutorial.progress'].search([
            ('tutorial_id', '=', self.id), ('user_id', '=', self.env.user.id),
        ])

    @api.model
    def _get_user_progresses(self):
        """ The progress of the current user in each tutorial they started """
        return self.env['web_tutorial.progress'].search([('user_id', '=', self.env.user.id)])

    def _is_accessible(self):
        """ Whether the current user can play the tutorial: they are in its
        groups, if any, and can open its starting action (its groups, if any,
        and reading its model) """
        self.ensure_one()
        if self.group_ids and not self.group_ids & self.env.user.all_group_ids:
            return False
        action = self._get_starting_action().sudo()
        if not action:
            return False
        if action.group_ids and not action.group_ids & self.env.user.all_group_ids:
            return False
        return action.res_model in self.env and self.env[action.res_model].has_access('read')
