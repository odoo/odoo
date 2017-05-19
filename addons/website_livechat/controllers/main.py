# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.tools import pycompat


class WebsiteLivechat(http.Controller):

    @http.route('/livechat/', type='http', auth="public", website=True)
    def channel_list(self, **kw):
        # display the list of the channel
        channels = request.env['im_livechat.channel'].search([('website_published', '=', True)])
        values = {
            'channels': channels
        }
        return request.render('website_livechat.channel_list_page', values)


    @http.route('/livechat/channel/<model("im_livechat.channel"):channel>', type='http', auth='public', website=True)
    def channel_rating(self, channel, **kw):
        # get the last 100 ratings and the repartition per grade
        ratings = request.env['rating.rating'].search([('res_model', '=', 'mail.channel'), ('res_id', 'in', channel.sudo().channel_ids.ids)], order='create_date desc', limit=100)
        repartition = channel.sudo().channel_ids.rating_get_grades()

        # compute percentage
        percentage = dict.fromkeys(['great', 'okay', 'bad'], 0)
        for grade in repartition:
            percentage[grade] = repartition[grade] * 100 / sum(pycompat.values(repartition)) if sum(pycompat.values(repartition)) else 0

        # the value dict to render the template
        values = {
            'channel': channel,
            'ratings': ratings,
            'team': channel.sudo().user_ids,
            'percentage': percentage
        }
        return request.render("website_livechat.channel_page", values)
