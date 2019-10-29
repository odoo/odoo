from odoo import models, api


class MassMailingCampaign(models.Model):
    _inherit = "mailing.mailing"

    @api.depends('mailing_model_real', 'contact_list_ids')
    def _compute_mailing_domain(self):
        # TDE FIXME: whuuut ?
        result = super(MassMailingCampaign, self)._compute_mailing_domain()
        for mailing in self:
            if mailing.mailing_model_name == 'event.registration' and mailing.mailing_domain == '[]':
                mailing.mailing_domain = self.env.context.get('default_mailing_domain', '[]')
        return result
