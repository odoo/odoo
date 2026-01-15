import re
from markupsafe import Markup

from odoo import api, models

CARD_IMAGE_URL = re.compile(r'src=".*?/web/image/card.campaign/[0-9]+/image_preview"')
CARD_PREVIEW_URL = re.compile(r'href=".*?/cards/[0-9]+/preview"')


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    def _prepare_mail_values_dynamic(self, res_ids):
        """Replace generic card urls with the specific res_id url."""
        mail_values_all = super()._prepare_mail_values_dynamic(res_ids)

        if campaign := self.mass_mailing_id.card_campaign_id:
            card_from_res_id = self.env['card.card'].search_fetch(
                [('campaign_id', '=', campaign.id), ('res_id', 'in', res_ids)],
                ['res_id'],
            ).grouped('res_id')

            processed_bodies = self._process_generic_card_url_body([
                (card_from_res_id[res_id], mail_values.get('body_html'))
                for res_id, mail_values in mail_values_all.items()
            ])
            for mail_values, body in zip(mail_values_all.values(), processed_bodies):
                if body is not None:
                    # in a mailing these are the same
                    mail_values['body'] = body
                    mail_values['body_html'] = body

        return mail_values_all

    def _get_done_emails(self, mail_values_dict):
        """Consider every target gets a different card, hence we don't want unique message per email address."""
        if self.mass_mailing_id.card_campaign_id:
            return []
        return super()._get_done_emails(mail_values_dict)

    @api.model
    def _process_generic_card_url_body(self, card_body_pairs: list[tuple[models.Model, str]]) -> list[str]:
        """Update the bodies with the specific card url for that res_id and create a card.

        example: (1, "/cards/9/preview") -> (1, "/cards/9/1/abchashtoken/preview") + new card as side-effect

        :return: processed bodies in the order they were received
        """
        bodies = []
        for card, body in card_body_pairs:
            if body:
                def fill_card_image_url(match):
                    return Markup('src="{}"').format(card._get_path('card.jpg'))

                def fill_card_preview_url(match):
                    return Markup('href="{}"').format(card._get_path('preview'))

                body_is_markup = False
                if isinstance(body, Markup):
                    body_is_markup = True
                body = re.sub(CARD_IMAGE_URL, fill_card_image_url, body)
                body = re.sub(CARD_PREVIEW_URL, fill_card_preview_url, body)
                if body_is_markup:
                    body = Markup(body)
            bodies.append(body)
        return bodies
