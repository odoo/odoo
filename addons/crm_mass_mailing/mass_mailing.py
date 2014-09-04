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

    @api.model
    def add_mail_and_utm_stuff(self, url):
        campaign = self.mass_mailing_campaign_id
        append =  '?' if url.find('?') == -1 else '&'
        url = "%s%sutm_campain=%s&utm_source=%s&utm_medium=%s" % (url, append, campaign.campaign_id.name, campaign.source_id.name, campaign.medium_id.name)
        return url

    @api.onchange('mass_mailing_campaign_id')
    def _onchange_mass_mailing_campaign_id(self):
        if self.mass_mailing_campaign_id:
            self.campaign_id = self.mass_mailing_campaign_id.campaign_id
            self.medium_id = self.mass_mailing_campaign_id.medium_id
            self.source_id = self.mass_mailing_campaign_id.source_id

    @api.multi
    def convert_link(self, body):
        if body:
            for long_url in self.find_urls(body):
                if self.mass_mailing_campaign_id:
                    long_url_with_utm = self.add_mail_and_utm_stuff(long_url)
                    body = body.replace(long_url, long_url_with_utm)
        return super(MassMailing, self).convert_link(body)

