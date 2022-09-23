# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.http import request
from odoo.addons.im_livechat.controllers.main import LivechatController


class WebsiteLivechat(LivechatController):

    @http.route('/livechat', type='http', auth="public", website=True, sitemap=True)
    def channel_list(self, **kw):
        # display the list of the channel
        channels = request.env['im_livechat.channel'].search([('website_published', '=', True)])
        values = {
            'channels': channels
        }
        return request.render('website_livechat.channel_list_page', values)

    @http.route('/livechat/channel/<model("im_livechat.channel"):channel>', type='http', auth='public', website=True, sitemap=True)
    def channel_rating(self, channel, **kw):
        # get the last 100 ratings and the repartition per grade
        domain = [
            ('res_model', '=', 'mail.channel'), ('res_id', 'in', channel.sudo().channel_ids.ids),
            ('consumed', '=', True), ('rating', '>=', 1),
        ]
        ratings = request.env['rating.rating'].sudo().search(domain, order='create_date desc', limit=100)
        repartition = channel.sudo().channel_ids.rating_get_grades(domain=domain)

        # compute percentage
        percentage = dict.fromkeys(['great', 'okay', 'bad'], 0)
        for grade in repartition:
            percentage[grade] = round(repartition[grade] * 100.0 / sum(repartition.values()), 1) if sum(repartition.values()) else 0

        # filter only on the team users that worked on the last 100 ratings and get their detailed stat
        ratings_per_partner = {partner_id: dict(great=0, okay=0, bad=0)
                               for partner_id in ratings.mapped('rated_partner_id.id')}
        total_ratings_per_partner = dict.fromkeys(ratings.mapped('rated_partner_id.id'), 0)
        # keep 10 for backward compatibility
        rating_texts = {10: 'great', 5: 'great', 3: 'okay', 1: 'bad'}

        for rating in ratings:
            partner_id = rating.rated_partner_id.id
            ratings_per_partner[partner_id][rating_texts[rating.rating]] += 1
            total_ratings_per_partner[partner_id] += 1

        for partner_id, rating in ratings_per_partner.items():
            for k, v in ratings_per_partner[partner_id].items():
                ratings_per_partner[partner_id][k] = round(100 * v / total_ratings_per_partner[partner_id], 1)

        # the value dict to render the template
        values = {
            'main_object': channel,
            'channel': channel,
            'ratings': ratings,
            'team': channel.sudo().user_ids,
            'percentage': percentage,
            'ratings_per_user': ratings_per_partner
        }
        return request.render("website_livechat.channel_page", values)

    @http.route('/im_livechat/get_session', type="json", auth='public', cors="*")
    def get_session(self, channel_id, anonymous_name, previous_operator_id=None, chatbot_script_id=None, **kwargs):
        """ Override to use visitor name instead of 'Visitor' whenever a visitor start a livechat session. """
        visitor_sudo = request.env['website.visitor']._get_visitor_from_request()
        if visitor_sudo:
            anonymous_name = visitor_sudo.with_context(lang=visitor_sudo.lang_id.code).display_name
        return super(WebsiteLivechat, self).get_session(channel_id, anonymous_name, previous_operator_id=previous_operator_id, chatbot_script_id=chatbot_script_id, **kwargs)

    def _livechat_templates_get(self):
        return super(WebsiteLivechat, self)._livechat_templates_get() + [
            'website_livechat/static/src/legacy/widgets/public_livechat_floating_text_view/public_livechat_floating_text_view.xml',
        ]
