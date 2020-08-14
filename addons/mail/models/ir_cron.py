# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import api, fields, models


class ir_cron(models.Model):
    _inherit = 'ir.cron'

    @api.model
    def _handle_callback_exception(self, cron_name, server_action_id, job_id, job_exception):
        """
            Method that overrides the original one from base to post a notification on admins channel.
        """
        super(ir_cron, self)._handle_callback_exception(cron_name, server_action_id, job_id, job_exception)
        # Get datetime when error occured != self.search([('id', '=', job_id)], limit=1).nextcall
        cron_error_datetime = fields.Datetime.now()
        job = self.browse(job_id)
        # Send notification to admin : errors related to cron job callback
        self._notify_admins(
            *self._get_admin_notification('base__cron')(
                job._format_record_link('go to scheduled action'),
                job_exception,
                cron_error_datetime,
                self._cr.dbname
            )
        )
