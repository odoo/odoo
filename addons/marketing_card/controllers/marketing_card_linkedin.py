import logging
from urllib.parse import urlencode
from werkzeug.exceptions import NotFound, Unauthorized

from odoo.exceptions import UserError
from odoo.http import Controller, request, route
from odoo.tools.urls import urljoin

from odoo.addons.marketing_card.utils.linkedin_api import LinkedInAPI

_logger = logging.getLogger(__name__)


class MarketingCardLinkedinController(Controller):
    _LINKEDIN_SHARE_CALLBACK_PATH = '/cards/share/linkedin/callback'

    @route(['/cards/<model("card.card"):card>/share/linkedin'], type='http', auth='public', website=True, sitemap=False)
    def linkedin_share_start(self, card, **kwargs):
        """Initiate LinkedIn OAuth flow for the visitor."""
        # if there is no image, there is no point in using the API as the basic url fallback is sufficient for text
        if card.image:
            try:
                url = LinkedInAPI(self.env).get_authorization_url(
                    redirect_uri=self._get_linkedin_card_share_redirect_uri(),
                    state=card.id, scope='w_member_social openid profile',
                )
                return request.redirect(url, local=False)
            except Exception as e:  # noqa: BLE001
                # UserError is expected in normal flow if the database does not have access to the feature
                log_level = logging.INFO if isinstance(e, UserError) else logging.WARNING
                _logger.log(log_level, 'Could not generate an authorization url for LinkedIn, falling back to url-based sharing.\n%s', e)

        # if there's an error we can just let people share "normally", using opengraph
        query_params = {
            'shareActive': 'true',
            'url': card._get_redirect_url(),
        }
        if post_suggestion := card.sudo().campaign_id.post_suggestion:
            query_params['text'] = post_suggestion
        url = f'https://www.linkedin.com/sharing/share-offsite/?{urlencode(query_params)}'

        return request.redirect(url, local=False)

    @route([_LINKEDIN_SHARE_CALLBACK_PATH], type='http', auth='public', website=True, sitemap=False)
    def linkedin_share_callback(self, state, access_token=None, code=None, error=None, **kwargs):
        """Expect a response either from IAP or linkedin.

        :param string|None access_token: a linkedin access token provided by IAP
        :param string|None code: a linkedin authorization code provided by linkedin
        :param string state: expected to be the id of the card we're posting, provided by both
        :param string|None error: an error string, provided by both
        """
        card_id = int(state)  # state is a standard oauth parameter, for now we only store the card_id in it
        card = self.env['card.card'].browse(card_id).exists()
        if not card:
            raise NotFound()
        campaign_sudo = card.sudo().campaign_id
        render_values = {
            'campaign_sudo': campaign_sudo,
            'card': card,
            'linkedin_auth_state': 'missing'
        }

        if error or (not access_token and not code):
            return request.render('marketing_card.card_campaign_linkedin_share_composer', render_values | {
                'linkedin_auth_state': 'missing'
            })

        if not access_token:
            try:
                linkedin_api = LinkedInAPI(self.env)
                access_token = linkedin_api.fetch_access_token(code, self._get_linkedin_card_share_redirect_uri())
            except UserError:
                return request.render('marketing_card.card_campaign_linkedin_share_composer', render_values | {
                    'linkedin_auth_state': 'error'
                })
        else:
            linkedin_api = LinkedInAPI(self.env, access_token=access_token)

        linkedin_user_info = linkedin_api.get_user_info()
        return request.render('marketing_card.card_campaign_linkedin_share_composer', render_values | {
            'linkedin_access_token': access_token,
            'linkedin_auth_state': 'success',
            'linkedin_user_fullname': linkedin_user_info.get('name'),
            'linkedin_user_picture_url': linkedin_user_info.get('picture'),
        })

    @route(['/cards/<model("card.card"):card>/share/linkedin/post'], type='http', methods=['POST'], auth='public', website=True, sitemap=False)
    def linkedin_post_card(self, card, linkedin_access_token, text=''):
        if not linkedin_access_token:
            raise Unauthorized()

        linkedin_api = LinkedInAPI(self.env, access_token=linkedin_access_token)
        linkedin_user_id = linkedin_api.get_user_info().get('sub')
        post_id = linkedin_api.post_image(
            linkedin_user_id, text=text, image_bytes=card.image.content, image_title=card.display_name, image_description=card.display_name,
        )

        return request.redirect(f"https://www.linkedin.com/feed/update/{post_id}", local=False)

    def _get_linkedin_card_share_redirect_uri(self):
        return urljoin(
            request.httprequest.url_root, MarketingCardLinkedinController._LINKEDIN_SHARE_CALLBACK_PATH,
        )
