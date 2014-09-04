from openerp import models, fields, api, _

class MassMailingCampaign(models.Model):
    _name = 'mail.mass_mailing.campaign'
    _inherit = ['mail.mass_mailing.campaign', 'crm.tracking.mixin']

    @api.multi
    def _get_souce_id(self):
        souce_id = self.env['ir.model.data'].get_object_reference('crm', 'crm_source_newsletter')
        return souce_id and souce_id[1] or False

    @api.multi
    def _get_medium_id(self):
        medium_id = self.env['ir.model.data'].get_object_reference('crm', 'crm_medium_email')
        return medium_id and medium_id[1] or False

    _defaults = {
        'source_id': lambda self, *args: self._get_souce_id(*args),
        'medium_id' : lambda self, *args: self._get_medium_id(*args),
    }

    @api.model
    def create(self, vals):
        if vals.get('name'):
            vals['campaign_id'] = self.env['crm.tracking.campaign'].create({'name': vals.get('name')}).id
        return super(MassMailingCampaign, self).create(vals)

class MassMailing(models.Model):
    _name = 'mail.mass_mailing'
    _inherit = ['mail.mass_mailing', 'crm.tracking.mixin']

    @api.onchange('mass_mailing_campaign_id')
    def _onchange_mass_mailing_campaign_id(self):
        if self.mass_mailing_campaign_id:
            self.campaign_id = self.mass_mailing_campaign_id.campaign_id
            self.medium_id = self.mass_mailing_campaign_id.medium_id
            self.source_id = self.mass_mailing_campaign_id.source_id

