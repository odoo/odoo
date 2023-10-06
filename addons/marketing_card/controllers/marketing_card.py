import base64
from urllib.parse import quote

from odoo.http import Controller, content_disposition, request, route
from odoo.tools import consteq
from odoo import _, exceptions


# from https://github.com/monperrus/crawler-user-agents
SOCIAL_NETWORK_USER_AGENTS = (
    # Facebook
    'Facebot',
    'facebookexternalhit',
    # Twitter
    'Twitterbot',
    # LinkedIn
    'LinkedInBot',
    # Whatsapp
    'WhatsApp',
    # Pinterest
    'Pinterest',
    'Pinterestbot',
)


def _check_url(campaign_id, res_id, hash_token):
    """Checks existence, token match and returns campaign, record and card as sudo."""
    campaign_sudo = request.env['card.campaign'].sudo().browse(campaign_id).exists()
    if not campaign_sudo or not consteq(hash_token, campaign_sudo._generate_card_hash_token(res_id)):
        raise request.not_found()

    target_sudo = request.env[campaign_sudo.res_model].sudo().browse(res_id).exists()
    if not target_sudo:
        raise request.not_found()

    card_sudo = campaign_sudo._get_or_create_cards_from_res_ids([res_id])

    return campaign_sudo, target_sudo, card_sudo


def _is_crawler(request):
    """Returns True if the request is made by a social network crawler."""
    return any(
        short_crawler_name in request.httprequest.user_agent.string
        for short_crawler_name in SOCIAL_NETWORK_USER_AGENTS
    )


class MarketingCardController(Controller):

    @route(['/cards/<int:campaign_id>/<int:res_id>/<string:hash_token>/status'], type='json', auth='public')
    def card_campaign_check_card_status(self, campaign_id, res_id, hash_token):
        """Used to check the status of the card after sharing button is clicked."""
        card_sudo = _check_url(campaign_id, res_id, hash_token)[2]
        return card_sudo.share_status

    @route(['/cards/<int:campaign_id>/<int:res_id>/<string:hash_token>/card.jpg'], type='http', auth='public', sitemap=False, website=True)
    def card_campaign_image(self, campaign_id, res_id, hash_token):

        card_sudo = _check_url(campaign_id, res_id, hash_token)[2]
        if _is_crawler(request) and card_sudo.share_status != 'shared':
            card_sudo.share_status = 'shared'

        image_b64 = card_sudo._get_or_generate_image()
        if not image_b64:
            raise exceptions.UserError(_("An error occurred when generating the image"))
        image_bytes = base64.b64decode(image_b64)
        return request.make_response(image_bytes, [
            ('Content-Type', ' image/jpeg'),
            ('Content-Length', len(image_bytes)),
            ('Content-Disposition', content_disposition('card.jpg')),
        ])

    @route(['/cards/<int:campaign_id>/<int:res_id>/<string:hash_token>/preview'], type='http', auth='public', sitemap=False, website=True)
    def card_campaign_preview(self, campaign_id, res_id, hash_token):
        """Route for users to preview their card and share it on their social platforms."""

        campaign_sudo, target_sudo, card_sudo = _check_url(campaign_id, res_id, hash_token)
        if not card_sudo.share_status:
            card_sudo.share_status = 'visited'

        return request.render('marketing_card.card_campaign_preview', {
            'image_url': card_sudo._get_card_url(),
            'link_shared': card_sudo.share_status == 'shared',
            'link_shared_reward_url': campaign_sudo.reward_target_url,
            'link_shared_thanks_message': campaign_sudo.reward_message,
            'post_text': quote(campaign_sudo.post_suggestion) if campaign_sudo.post_suggestion else '',
            'share_url': card_sudo._get_redirect_url(),
            'share_url_quoted': quote(card_sudo._get_redirect_url()),
            'target_name': target_sudo.display_name or '',
        })

    @route(['/cards/<int:campaign_id>/<int:res_id>/<string:hash_token>/redirect'], type='http', auth='public', sitemap=False, website=True)
    def card_campaign_redirect(self, campaign_id, res_id, hash_token):
        """Route to redirect users to the target url, or display the opengraph embed text for web crawlers.

        When a user posts a link on an application supporting opengraph, the application will follow
        the link to fetch specific meta tags on the web page to get preview information such as a preview card.
        The "crawler" performing that action usually has a specific user agent.

        As we cannot necessarily control the target url of the campaign we must return a different
        result when a social network crawler is visiting the URL to get preview information.
        From the perspective of the crawler, this url is an empty page with opengraph tags.
        For all other user agents, it's a simple redirection url.

        Keeping an up-to-date list of user agents for each supported target website is imperative
        for this app to work.
        """
        campaign_sudo, target_sudo, card_sudo = _check_url(campaign_id, res_id, hash_token)
        redirect_url = campaign_sudo.link_tracker_id.short_url or campaign_sudo.target_url or campaign_sudo.get_base_url()

        if _is_crawler(request):
            return request.render('marketing_card.card_campaign_crawler', {
                'image_url': card_sudo._get_card_url(),
                'post_text': campaign_sudo.post_suggestion,
                'target_name': target_sudo.display_name or '',
            })

        return request.redirect(redirect_url)
