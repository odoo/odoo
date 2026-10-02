# Part of web_progress. See LICENSE file for full copyright and licensing details.
from odoo import models, api, registry, fields, _
import uuid


class IrCron(models.Model):
    _inherit = 'ir.cron'

    @api.model
    def _callback(self, cron_name, server_action_id, job_id):
        """
        Add web progress code if it does not exist.
        This allows to report progress of cron-executed jobs
        """
        new_self = 'progress_code' in self._context and self or self.with_context(progress_code=str(uuid.uuid4()))
        return super(IrCron, new_self)._callback(cron_name, server_action_id, job_id)