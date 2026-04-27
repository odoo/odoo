# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    def action_new_quotation(self):
        action = super().action_new_quotation()
        # Make the lead's Assigned Partner the quotation's Referrer.
        action['context']['default_referrer_id'] = self.partner_assigned_id.id
        return action
