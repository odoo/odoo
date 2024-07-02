import base64

from odoo.http import Controller, content_disposition, request, route

from .user_agents import NETWORK_TO_AGENT
from ..utils.image_utils import scale_image

class MarketingCardController(Controller):

    @route(['/cards/<int:campaign_id>/<int:res_id>/<string:hash_token>/card.jpg'], type='http', auth='public', sitemap=False, website=True)
    def card_campaign_image(self, campaign_id, res_id, hash_token, small=False):
        campaign = request.env['card.campaign'].sudo().browse(campaign_id).exists()
        if not campaign or hash_token != campaign._generate_card_hash_token(res_id):
            raise request.not_found()

        target = request.env[campaign.res_model].sudo().browse(res_id).exists()
        if not target:
            return request.not_found()

        card = campaign._get_or_create_card_from_res_id(res_id)

        crawler = self._get_crawler_name(request)
        if crawler and not card.is_shared:
            request.env['bus.bus']._sendone(f'card_shared_target-{campaign_id}-{hash_token}', 'marketing_card/share_card_target', {
                'message': campaign.thanks_message,
                'reward_url': campaign.thanks_redirection,
            })
            card.is_shared = True

        if all(element.value_type != 'static' for element in campaign.element_ids):
            image_bytes = base64.b64decode(campaign.image)
        else:
            image_bytes = base64.b64decode(card._get_or_generate_image())
        image_bytes = image_bytes if not small else scale_image(image_bytes, 0.5)
        return request.make_response(image_bytes, [
            ('Content-Type', ' image/jpeg'),
            ('Content-Length', len(image_bytes)),
            ('Content-Disposition', content_disposition('card.jpg')),
        ])

    @route(['/cards/<int:campaign_id>/card.jpg'])
    def card_campaign_image_placeholder(self, campaign_id):
        """Mostly useful for previews in mass mailing."""
        campaign = request.env['card.campaign'].sudo().browse(campaign_id).exists()
        if not campaign:
            return request.not_found()
        image_bytes = base64.b64decode(campaign.image)
        return request.make_response(image_bytes, [
            ('Content-Type', ' image/jpeg'),
            ('Content-Length', len(image_bytes)),
            ('Content-Disposition', content_disposition('card.jpg')),
        ])

    @route(['/cards/<int:campaign_id>/<int:res_id>/<string:hash_token>/preview'], type='http', auth='public', sitemap=False, website=True)
    def card_campaign_preview(self, campaign_id, res_id, hash_token):
        """Route for users to preview their card and share it on their social platforms."""
        campaign = request.env['card.campaign'].sudo().browse(campaign_id).exists()
        if not campaign or hash_token != campaign._generate_card_hash_token(res_id):
            return request.not_found()

        target = request.env[campaign.res_model].sudo().browse(res_id).exists()
        if not target:
            return request.not_found()

        card = campaign._get_or_create_card_from_res_id(res_id)
        card.is_visited = True

        return request.render('marketing_card.card_campaign_preview', {
            'campaign_id': campaign_id,
            'image_url': card._get_card_url(small=True),
            'link_shared_thanks_message': campaign.thanks_message if card.is_shared else '',
            'link_shared_reward_url': campaign.thanks_redirection if card.is_shared else '',
            'post_text': campaign.post_suggestion or '',
            'redirect_url': card._get_redirect_url(),
            'share_url': card._get_redirect_url(),
            'target_name': target.display_name if target else '',
            'hash_token': hash_token,
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
        campaign = request.env['card.campaign'].sudo().browse(campaign_id).exists()
        if not campaign or hash_token != campaign._generate_card_hash_token(res_id):
            return request.not_found()

        target = request.env[campaign.res_model].sudo().browse(res_id).exists()
        if not target:
            return request.not_found()

        card = campaign._get_or_create_card_from_res_id(res_id)
        redirect_url = campaign.target_url_redirected

        crawler = self._get_crawler_name(request)
        if crawler:
            return request.render('marketing_card.card_campaign_crawler', {
                'image_url': card._get_card_url(),
                'post_text': campaign.post_suggestion,
                'target_name': target.name if target and 'name' in target else '',
            })

        return request.redirect(redirect_url)

    @staticmethod
    def _get_crawler_name(request):
        """Return the name of the social network for the user agent, if any."""
        user_agent = request.httprequest.user_agent.string
        for social_network, agent_names in NETWORK_TO_AGENT.items():
            if any(agent_name in user_agent for agent_name in agent_names):
                return social_network
        return ''
