# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

from datetime import datetime


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    def _merge_method(self, destination, source):
        tickets = destination + source
        status_list = self.env['helpdesk.sla.status']

        # datetime.max is in case one of the merged ticket is in a stage with "sla_id.exclude_stage_ids"
        for status in tickets.mapped('sla_status_ids').grouped('sla_id').values():
            status_list += min(status, key=lambda s: s.deadline or datetime.max)

        self.env['data_merge.record']._update_foreign_keys(destination, source)
        destination.update({'sla_status_ids': status_list, 'sla_ids': status_list.mapped('sla_id')})
        return {'post_merge': True, 'log_chatter': True}
