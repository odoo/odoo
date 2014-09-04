import re
from openerp import models, fields, api, _

URL_REGEX = r'https?://[^\s<>"]+|www\.[^\s<>"]+'

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
    _inherit = ['mail.mass_mailing']

    @api.model
    def add_mail_and_utm_stuff(self, url):
        campaign = self.mass_mailing_campaign_id
        append =  '?' if url.find('?') == -1 else '&'
        url = "%s%sutm_campain=%s&utm_source=%s&utm_medium=%s" % (url, append, campaign.name, campaign.source_id.name, campaign.medium_id.name)
        return url

    @api.multi
    def convert_link(self, body):
        urls = re.findall(URL_REGEX, body)
        for long_url in urls:
            if self.mass_mailing_campaign_id:
                long_url_with_utm = self.add_mail_and_utm_stuff(long_url)
                body = body.replace(long_url, long_url_with_utm)
        return super(MassMailing, self).convert_link(body)

