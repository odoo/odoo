from odoo import models
from odoo.exceptions import UserError


class MailActivitySchedule(models.TransientModel):
    _inherit = "mail.activity.schedule"

    def action_create_calendar_event(self):
        self.check_singleton()
        if self.is_batch_mode:
            raise UserError(
                self.env._(
                    "Scheduling an activity using the calendar is not possible on more than one record."
                )
            )
        if not self.res_model:
            return self._action_schedule_activities_personal().action_create_calendar_event()
        res_ids = self._evaluate_res_ids()
        if not res_ids:
            raise UserError(
                self.env._("There is no record to schedule this activity on.")
            )
        return (
            self.with_context(
                {
                    "default_res_model": self.res_model or False,
                    "default_res_id": res_ids[0],
                }
            )
            ._action_schedule_activities()
            .action_create_calendar_event()
        )
