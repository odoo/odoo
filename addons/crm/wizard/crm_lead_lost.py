# -*- coding: utf-8 -*-

from odoo import api, fields, models


class CrmLeadLost(models.TransientModel):
    _name = 'crm.lead.lost'
    _description = 'Get Lost Reason'

    lead_id = fields.Many2one('crm.lead', 'Lead', required=True)
    lost_reason_id = fields.Many2one('crm.lost.reason', 'Lost Reason')

    @api.multi
    def action_lost_reason_apply(self):
        self.lead_id.lost_reason = self.lost_reason_id
        return self.lead_id.action_set_lost()
