import re
from collections import defaultdict

from odoo import api, models
from odoo.addons.web.models.models import lazymapping


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
        campaign_tokens = lazymapping(
            lambda campaign_res_id:
                self.env['card.campaign'].browse(campaign_res_id[0])._generate_card_hash_token(campaign_res_id[1])
        )
        bodies = []
        for res_id, body in res_id_body_pairs:
            if body:
                def fill_card_image_url(match):
                    campaign_id = int(match[3])
                    return f'{match[1]}/cards/{campaign_id}/{res_id}/{campaign_tokens[(campaign_id, res_id)]}/card.jpg"'

                def fill_card_preview_url(match):
                    campaign_id = int(match[2])
                    return f'{match[1]}/{campaign_id}/{res_id}/{campaign_tokens[(campaign_id, res_id)]}/preview"'

                body = re.sub(CARD_IMAGE_URL, fill_card_image_url, body)
                body = re.sub(CARD_PREVIEW_URL, fill_card_preview_url, body)
            bodies.append(body)

        self._create_cards_if_not_exists(list(campaign_tokens))

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

    def _create_cards_if_not_exists(self, campaign_res_id_pairs):
        """Batch create new cards from multiple different campaigns."""
        if not campaign_res_id_pairs:
            return

        res_ids_from_campaign_id = defaultdict(list)
        for campaign_id, res_id in campaign_res_id_pairs:
            res_ids_from_campaign_id[campaign_id].append(res_id)

        for campaign_id, res_ids in res_ids_from_campaign_id.items():
            self.env['card.campaign'].browse(campaign_id).sudo()._get_or_create_cards_from_res_ids(res_ids)
