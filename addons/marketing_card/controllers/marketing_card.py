from urllib.parse import quote

from odoo.http import Controller, request, route
from odoo.http.stream import content_disposition

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


class MarketingCardController(Controller):

    @route(['/cards/<model("card.card"):card>/card.jpg'], type='http', auth='public', sitemap=False, website=True)
    def card_campaign_image(self, card):
        if _is_crawler(request) and card.share_status != 'shared':
            card.sudo().share_status = 'shared'
        if not card.image:
            raise request.not_found()

        image_bytes = card.image.content
        return request.make_response(image_bytes, [
            ('Content-Type', ' image/jpeg'),
            ('Content-Length', len(image_bytes)),
            ('Content-Disposition', content_disposition('card.jpg')),
        ])

    @route(['/cards/<model("card.card"):card>/preview'], type='http', auth='public', sitemap=False, website=True)
    def card_campaign_preview(self, card):
        """Route for users to preview their card and share it on their social platforms."""
        card = card.with_context(lang=card.lang)
        if not card.share_status:
            card.sudo().share_status = 'visited'

        campaign_sudo = card.sudo().campaign_id
        # ensure the page is displayed in the language of the card by default
        request.update_context(lang=card.lang)
        return request.render('marketing_card.card_campaign_preview', {
            'campaign': campaign_sudo,
            'card': card,
            'edit_in_backend': True,
            'main_object': campaign_sudo,
            'quote': quote,
        })

    @route(['/cards/<model("card.card"):card>/redirect'], type='http', auth='public', sitemap=False, website=True)
    def card_campaign_redirect(self, card):
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
        campaign_sudo = card.sudo().campaign_id
        record_sudo = self.env[card.res_model].browse(card.res_id).sudo().exists()

        record_url = None
        untracked_url = campaign_sudo.target_url
        if not untracked_url and record_sudo:
            untracked_url = record_url = campaign_sudo._get_record_url(record_sudo)
        if not untracked_url:
            untracked_url = campaign_sudo.get_base_url()

        # don't count clicks from preview
        if card.active:
            if record_url:
                redirect_url = untracked_url
                # still track on the link tracker since it's meant to track across the whole campaign
                if link_tracker_code := campaign_sudo.link_tracker_id.code:
                    request.env['link.tracker.click'].sudo().add_click(
                        link_tracker_code,
                        ip=request.httprequest.remote_addr,
                        country_code=request.geoip.country_code,
                    )
            else:
                redirect_url = campaign_sudo.link_tracker_id.short_url or untracked_url
        else:
            redirect_url = untracked_url

        if _is_crawler(request):
            return request.render('marketing_card.card_campaign_crawler', {
                'image_url': card._get_card_url(),
                'post_suggestion': campaign_sudo.post_suggestion,
                'target_name': card.display_name or '',
            })

        return request.redirect(redirect_url)
