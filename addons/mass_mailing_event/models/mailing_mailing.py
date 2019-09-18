from odoo import models, api


class MassMailingCampaign(models.Model):
    _inherit = "mailing.mailing"

    @api.onchange('mailing_model_real', 'contact_list_ids')
    def _onchange_model_and_list(self):
        # TDE FIXME: whuuut ?
        result = super(MassMailingCampaign, self)._onchange_model_and_list()
        if self.mailing_model_name == 'event.registration' and self.mailing_domain == '[]':
            self.mailing_domain = self.env.context.get('default_mailing_domain', '[]')
        return result
