# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MailActivityScheduleCall(models.TransientModel):
    """ The activity scheduling wizard, as opened to log a call that took place on a
    document. """
    _name = 'mail.activity.schedule.call'
    _inherit = 'mail.activity.schedule'
    _description = 'Log a call as an activity in a chatter'

    call_history_id = fields.Many2one('discuss.call.history', export_string_translation=False)
    is_call_ongoing = fields.Boolean(
        compute='_compute_is_call_ongoing', export_string_translation=False)

    def _get_logged_call(self):
        """ The call being logged, which a module with a call of its own overrides. Such
        a call answers `_is_call_ongoing` and `_link_to_logged_activity`. """
        self.ensure_one()
        return self.call_history_id

    def _get_logged_call_depends(self):
        """ The dependencies of what is computed from the logged call, which a module
        overriding `_get_logged_call` extends. """
        return ('call_history_id.end_dt',)

    @api.depends(lambda self: self._get_logged_call_depends())
    def _compute_is_call_ongoing(self):
        for scheduler in self:
            call = scheduler._get_logged_call()
            scheduler.is_call_ongoing = bool(call) and call._is_call_ongoing()

    def _action_schedule_activities(self):
        activities = super()._action_schedule_activities()
        # a personal activity is on no document: the call has no chatter to show up in
        if self.res_model and (call := self._get_logged_call()):
            call._link_to_logged_activity(activities[:1], self._get_partner_from_target())
        return activities
