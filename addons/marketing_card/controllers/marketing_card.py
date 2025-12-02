import base64
from urllib.parse import quote
from werkzeug.exceptions import BadRequest

from odoo.http import Controller, content_disposition, request, route

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


def _is_crawler(request):
    """Returns True if the request is made by a social network crawler."""
    return any(
        short_crawler_name in request.httprequest.user_agent.string
        for short_crawler_name in SOCIAL_NETWORK_USER_AGENTS
    )


def _get_card_from_url(card_id, card_slug):
    """Helper to support both legacy card id url and new slug urls"""
    if card_slug:
        card_id = request.env['ir.http']._unslug(card_slug)[1]
    if not card_id:
        raise request.not_found()
    card = request.env['card.card'].browse(card_id).exists()
    if not card:
        raise BadRequest()
    return card


class MarketingCardController(Controller):

    @route([
        '/cards/<string:card_slug>/card.jpg',
        '/cards/<int:card_id>/card.jpg',
    ], type='http', auth='public', sitemap=False, website=True)
    def card_campaign_image(self, card_id=None, card_slug=None):
        card = _get_card_from_url(card_id, card_slug)
        if _is_crawler(request) and card.share_status != 'shared':
            card.sudo().share_status = 'shared'
        if not card.image:
            raise request.not_found()

        image_bytes = base64.b64decode(card.image)
        return request.make_response(image_bytes, [
            ('Content-Type', ' image/jpeg'),
            ('Content-Length', len(image_bytes)),
            ('Content-Disposition', content_disposition('card.jpg')),
        ])

    @route([
        '/cards/<string:card_slug>/preview',
        '/cards/<int:card_id>/preview',
    ], type='http', auth='public', sitemap=False, website=True)
    def card_campaign_preview(self, card_id=None, card_slug=None):
        """Route for users to preview their card and share it on their social platforms."""
        card = _get_card_from_url(card_id, card_slug)
        if not card.share_status:
            card.sudo().share_status = 'visited'

        campaign_sudo = card.sudo().campaign_id
        return request.render('marketing_card.card_campaign_preview', {
            'card': card,
            'campaign': campaign_sudo,
            'quote': quote,
        })

    @route([
        '/cards/<string:card_slug>/redirect',
        '/cards/<int:card_id>/redirect',
    ], type='http', auth='public', sitemap=False, website=True)
    def card_campaign_redirect(self, card_id=None, card_slug=None):
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
        card = _get_card_from_url(card_id, card_slug)

        campaign_sudo = card.sudo().campaign_id
        # don't count clicks from preview
        redirect_url = campaign_sudo.target_url or campaign_sudo.get_base_url()
        if card.active:
            redirect_url = campaign_sudo.link_tracker_id.short_url or redirect_url

        if _is_crawler(request):
            return request.render('marketing_card.card_campaign_crawler', {
                'image_url': card._get_card_url(),
                'post_text': campaign_sudo.post_suggestion,
                'target_name': card.display_name or '',
            })

        return request.redirect(redirect_url)
