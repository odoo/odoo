# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup
from odoo import fields, models, _
from odoo.tools.mail import is_html_empty


class CrmLeadLost(models.TransientModel):
    _name = 'crm.lead.lost'
    _description = 'Get Lost Reason'

    lead_ids = fields.Many2many('crm.lead')
    lost_reason_id = fields.Many2one('crm.lost.reason', 'Lost Reason')
    lost_feedback = fields.Html(
        'Closing Note', sanitize=True
    )

    def action_lost_reason_apply(self):
        """Mark lead as lost and apply the loss reason"""
        self.ensure_one()
        # get lead from context for retro-compatibility
        if not self.lead_ids and self.env.context.get('active_model', '') == 'crm.lead':
            ctx = self.env.context
            ctx_lead_ids = ctx.get('active_ids') or [ctx['active_id']] if ctx.get('active_id') else []
            self.lead_ids = self.lead_ids.browse(ctx_lead_ids)

        if not is_html_empty(self.lost_feedback):
            self.lead_ids._track_set_log_message(
                Markup('<div style="margin-bottom: 4px;"><p>%s:</p>%s<br /></div>') % (
                    _('Lost Comment'),
                    self.lost_feedback
                )
            )
        res = self.lead_ids.action_set_lost(lost_reason_id=self.lost_reason_id.id)
        return res
