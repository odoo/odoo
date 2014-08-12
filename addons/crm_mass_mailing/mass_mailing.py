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

    @api.model
    def convert_link(self, body):
        urls = re.findall(URL_REGEX, body)
        website_alias = self.env['website.alias']
        for long_url in urls:
            if self.mass_mailing_campaign_id:
                long_url_with_utm = self.add_mail_and_utm_stuff(long_url)
                shorten_url = website_alias.create_shorten_url(long_url_with_utm)
            else:
                shorten_url = website_alias.create_shorten_url(long_url)
            if shorten_url:
                body = body.replace(long_url, shorten_url)
        return body

    @api.one
    def send_mail(self):
        for mailing in self:
            self.body_html = self.convert_link(mailing.body_html)
        return super(MassMailing, self).send_mail()

class MailMail(models.Model):
    _inherit = ['mail.mail']

    def send_get_mail_body(self, cr, uid, mail, partner=None, context=None):
        """ Override to add Statistic_id in shorted urls """
        if mail.mailing_id.mass_mailing_campaign_id:
            urls = re.findall(URL_REGEX, mail.body_html)
            for url in urls:
                mail.body_html = mail.body_html.replace(url, url + '/m/' + str(mail.statistics_ids.id))
            body = super(MailMail, self).send_get_mail_body(cr, uid, mail, partner=partner, context=context)
            return body
        else:
            return mail.body_html
