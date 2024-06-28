from odoo import models


class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    def get_crm_lead_vals(self, partner, key, customers):
        lead_vals = super().get_crm_lead_vals(partner, key, customers)
        utm_source = self.env.ref('crm_livechat_whatsapp.utm_source_whatsapp', raise_if_not_found=False)
        utm_medium = self.env.ref('crm_livechat_whatsapp.utm_medium_whatsapp', raise_if_not_found=False)
        lead_vals['source_id'] = utm_source and utm_source.id,
        lead_vals['medium_id'] = utm_medium and utm_medium.id
        return lead_vals
