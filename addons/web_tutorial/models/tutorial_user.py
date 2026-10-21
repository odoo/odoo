from odoo import api, fields, models
from odoo.addons.web.controllers.utils import get_action


class TutorialUser(models.Model):
    """ The progress of a user in a tutorial, only reached with sudo """
    _name = 'web_tutorial.tutorial.user'
    _description = "Tutorial Progress"

    done = fields.Boolean(help="Whether the user finished, skipped or marked as done the tutorial")
    done_steps = fields.Json(help="The keys of the steps of the tutorial the user did")
    played_date = fields.Datetime(help="When the user last played the tutorial from the list of their tutorials")
    resume_url = fields.Char()
    tutorial_id = fields.Many2one("web_tutorial.tutorial", required=True, ondelete="cascade")
    user_id = fields.Many2one("res.users", required=True, index=True, ondelete="cascade")

    _uniq_tutorial_user = models.Constraint('unique(tutorial_id, user_id)', "A user has one progress by tutorial.")

    def _get_resume_url(self):
        """ The saved URL to resume the tutorial at, stopping at the action of
        a record deleted or not readable anymore, e.g. with the lead 12 deleted:

        - ``/odoo/crm/12`` resumes at ``/odoo/crm/new``;
        - ``/odoo/crm/12/action-42/7`` resumes at ``/odoo/crm``.

        :return: the URL, or False if none or if an action doesn't exist
        """
        if not self.resume_url:
            return False
        prefix, _sep, path = self.resume_url.partition('?')[0].strip('/').partition('/')
        segments = self._split_path(path)
        for index, (action_path, record) in enumerate(segments):
            action = get_action(self.env, action_path)
            if not action:
                return False
            if not record or record == 'new':
                continue
            model = action.res_model if 'res_model' in action._fields else None
            if model in self.env and not self._is_record_readable(self.env[model].with_user(self.user_id).browse(int(record))):
                is_last = index == len(segments) - 1
                kept = [*segments[:index], (action_path, 'new' if is_last else None)]
                return '/' + '/'.join([prefix, *(token for segment in kept for token in segment if token)])
        return self.resume_url

    @api.model
    def _is_record_readable(self, record):
        """ Whether the record exists and the current user can read it (e.g.
        not a record of another company) """
        return bool(record.exists()) and record.has_access('read')

    @api.model
    def _split_path(self, path):
        """ Split a path of the web client into its actions with their record,
        e.g. ``crm/12/action-42`` into ``[('crm', '12'), ('action-42', None)]`` """
        segments = []
        for token in path.split('/') if path else []:
            if segments and segments[-1][1] is None and (token == 'new' or token.isdigit()):
                segments[-1] = (segments[-1][0], token)
            else:
                segments.append((token, None))
        return segments
