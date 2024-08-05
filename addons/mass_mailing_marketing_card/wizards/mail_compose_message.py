import re

from odoo import api, models

CARD_IMAGE_URL = re.compile(r'(src=".*)(/web/image/card.campaign/)([0-9]+)/image_preview"')
CARD_PREVIEW_URL = re.compile(r'(href=".*/cards)/([0-9]+)/preview"')


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.model
    def _process_generic_card_url_body(self, res_id_body_pairs: list[tuple[int, str]]) -> list[str]:
        """Update the bodies with the specific card url for that res_id and create a card.

        example: (1, "/cards/9/preview") -> (1, "/cards/9/1/abchashtoken/preview") + new card as side-effect

        :return: processed bodies in the order they were received
        """
        bodies = []
        for res_id, body in res_id_body_pairs:
            if body:
                def fill_card_image_url(match):
                    card = self.env['card.card'].browse(int(match[3]))
                    return 'href="' + card._get_path('card.jpg') + '"'

                def fill_card_preview_url(match):
                    card = self.env['card.card'].browse(int(match[2]))
                    return 'href="' + card._get_path('preview') + '"'

                body = re.sub(CARD_IMAGE_URL, fill_card_image_url, body)
                body = re.sub(CARD_PREVIEW_URL, fill_card_preview_url, body)
            bodies.append(body)
        return bodies

    def _prepare_mail_values(self, res_ids):
        """Replace generic card urls with the specific res_id url."""

        mail_values_all = super()._prepare_mail_values(res_ids)

        processed_bodies = self._process_generic_card_url_body([
            (res_id, mail_values.get('body_html'))
            for res_id, mail_values in mail_values_all.items()
        ])
        for mail_values, body in zip(mail_values_all.values(), processed_bodies):
            if body is not None:
                mail_values['body_html'] = body

        return mail_values_all
