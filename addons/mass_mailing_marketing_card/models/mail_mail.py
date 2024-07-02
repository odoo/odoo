import re

from odoo import models, tools


class MailMail(models.Model):
    """Add custom card url to mailings"""
    _inherit = ['mail.mail']

    def _prepare_outgoing_body_apply_mailing_tracking(self, body):
        """Update mailing specific links to replace generic card urls with email-specific links."""
        if not self.res_id or not self.mailing_id:
            return super()._prepare_outgoing_body_apply_mailing_tracking(body)

        card_values = set()
        for match in set(re.findall(r'<img.*?src="((.*?/cards/([0-9]+))/card.jpg)"', body)):
            full_url = match[0]
            url_start = match[1]
            campaign_id = int(match[2])
            card_token = self.env['card.campaign'].browse(campaign_id)._generate_card_hash_token(self.res_id)
            card_values.add(tools.frozendict({'campaign_id': campaign_id, 'res_id': self.res_id}))
            body = body.replace(full_url, f'{url_start}/{self.res_id}/{card_token}/card.jpg')
        for match in set(re.findall(r'<.*?href="((.*?/cards/([0-9]+))/preview)"', body)):
            full_url = match[0]
            url_start = match[1]
            campaign_id = int(match[2])
            card_token = self.env['card.campaign'].browse(campaign_id)._generate_card_hash_token(self.res_id)
            card_values.add(tools.frozendict({'campaign_id': campaign_id, 'res_id': self.res_id}))
            body = body.replace(full_url, f'{url_start}/{self.res_id}/{card_token}/preview')

        # defer creation of cards used for tracking sent count
        marketing_card_values = self.env.cr.precommit.data.setdefault('marketing_card_create_cards_values', [])
        marketing_card_values.extend(list(card_values))
        self.env.cr.precommit.add(self.env['card.card']._deferred_create)

        return super()._prepare_outgoing_body_apply_mailing_tracking(body)
