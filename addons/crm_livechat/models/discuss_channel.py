# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    def _get_crm_lead_vals(self, partner, key, customers):
        lead_vals = super()._get_crm_lead_vals(partner, key, customers)
        if self.channel_type == 'livechat':
            utm_source = self.env.ref('crm_livechat.utm_source_livechat', raise_if_not_found=False)
            lead_vals['source_id'] = utm_source and utm_source.id
        return lead_vals
