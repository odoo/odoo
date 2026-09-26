# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class IrCron(models.Model):
    _inherit = 'ir.cron'

    @api.model
    def _clear_schedule(self, job):
        # update the alarms in the cron runner transaction, as doing so potentially
        # writes to the cron trigger that is deleted in super. In that case
        # the job transaction waits for the runner transaction to finish, which only
        # happens after the job times out. Then we end up in a state where the alarm
        # trigger was deleted here, and not rescheduled, meaning it will never run again.
        super()._clear_schedule(job)
        alarm_cron = self.env.ref('calendar.ir_cron_scheduler_alarm', raise_if_not_found=False)
        if alarm_cron and job['id'] == alarm_cron.id:
            self.env['calendar.alarm_manager'].with_context(
                lastcall=job['lastcall'],
            )._reschedule_recurrent_alarms()
