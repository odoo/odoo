from odoo.http import Controller, request, route

from .user_agents import NETWORK_TO_AGENT

class SocialShareController(Controller):

    @route(['/social_share/<int:campaign_id>/card.png', '/social_share/<int:campaign_id>/<string:uid>/card.png'], type='http', auth='public', sitemap=False, website=True)
    def social_share_campaign_image(self, campaign_id=0, uid=None):
        campaign = request.env['social.share.campaign'].sudo().browse(campaign_id).exists()
        url = request.env['social.share.url']
        target = None
        if campaign.model_id:
            if not uid:
                return request.not_found()
            url = request.env['social.share.url'].sudo().search([('campaign_id', '=', campaign.id), ('uuid', '=', uid)])
            target = request.env[campaign.model_id.model].sudo().browse(url.res_id).exists()

        crawler = self._get_crawler_name(request)
        if crawler:
            request.env['bus.bus']._sendone(f'social_share_url_target-{uid}', 'social_share/share_url_target', {
                'message': campaign.thanks_message,
                'reward_url': campaign.thanks_redirection,
            })
            url.shared = True

        image_bytes = campaign.sudo()._generate_image_bytes(record=target)
        return request.make_response(image_bytes, [('Content-Type', ' image/png')])

    @route(['/social_share/campaign/<int:campaign_id>', '/social_share/campaign/<int:campaign_id>/<string:uid>'], type='http', auth='public', sitemap=False, website=True)
    def social_share_campaign_visitor(self, campaign_id=0, uid=None):
        """Route for users to preview their card and share it on their social platforms."""
        campaign = request.env['social.share.campaign'].sudo().browse(campaign_id).exists()

        if not campaign:
            return request.not_found()

        target = None

        url = request.env['social.share.url']
        if campaign.model_id:
            if not uid:
                return request.not_found()
            url = request.env['social.share.url'].sudo().search([('campaign_id', '=', campaign.id), ('uuid', '=', uid)])
            url.visited = True
            target = request.env[campaign.model_id.model].sudo().browse(url.res_id).exists()
            if not target:
                return request.not_found()

        return request.render('social_share.share_campaign_visitor', {
            'image_url': self._get_card_url(campaign_id, uid),
            'link_shared_message': campaign.thanks_message,
            'link_shared_reward_url': campaign.thanks_redirection if url.shared else '',
            'post_text': campaign.post_suggestion,
            'redirect_url': self._get_redirect_url(campaign_id, uid),
            'share_url': self._get_redirect_url(campaign_id, uid),
            'target_name': target.display_name if target else '',
            'uuid': uid,
        })

    @route(['/social_share/redirect/<int:campaign_id>', '/social_share/redirect/<int:campaign_id>/<string:uid>'], type='http', auth='public', sitemap=False, website=True)
    def social_share_campaign_redirect(self, campaign_id=0, uid=None):
        """Route to redirect users to the target url, or display the opengraph embed text for web crawlers."""
        campaign = request.env['social.share.campaign'].sudo().browse(campaign_id).exists()
        if not campaign:
            return request.not_found()
        target = False

        url = request.env['social.share.url']
        if campaign.model_id:
            if not uid:
                return request.not_found()
            url = request.env['social.share.url'].sudo().search([('campaign_id', '=', campaign.id), ('uuid', '=', uid)])
            target = request.env[campaign.model_id.model].sudo().browse(url.res_id).exists()
            if not target:
                return request.not_found()

        redirect_url = campaign.target_url_redirected

        crawler = self._get_crawler_name(request)
        if crawler:
            return request.render('social_share.share_campaign_crawler', {
                'image_url': self._get_card_url(campaign_id, uid),
                'target_name': target.name if target and 'name' in target else '',
                'post_text': campaign.post_suggestion,
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

    @staticmethod
    def _get_card_url(share_campaign_id, uid):
        base = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base}/social_share/{share_campaign_id}/{f'{uid}/' if uid else ''}card.png"

    @staticmethod
    def _get_redirect_url(share_campaign_id, uid):
        base = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f'{base}/social_share/redirect/{share_campaign_id}' + (f'/{uid}' if uid else '')

    @staticmethod
    def _get_campaign_url(share_campaign_id, uid):
        base = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f'{base}/social_share/campaign/{share_campaign_id}' + (f'/{uid}' if uid else '')
