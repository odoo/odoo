# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.tools.mail import is_html_empty


class CrmLeadLost(models.TransientModel):
    _name = 'crm.lead.lost'
    _description = 'Get Lost Reason'

    lost_reason_id = fields.Many2one('crm.lost.reason', 'Lost Reason')
    lost_feedback = fields.Html(
        'Closing Note', sanitize=True,
        help="Closing note logged in leads discussion history."
    )

    def action_lost_reason_apply(self):
        self.ensure_one()
        leads = self.env['crm.lead'].browse(self.env.context.get('active_ids'))
        res = leads.action_set_lost(lost_reason=self.lost_reason_id.id)
        if not is_html_empty(self.lost_feedback):
            leads._message_log_batch(
                bodies=dict(
                    (lead.id, self.lost_feedback)
                    for lead in leads),
                subject=False,
            )
        return res
