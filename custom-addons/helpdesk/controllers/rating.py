# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import http
from odoo.http import request
from odoo.osv.expression import AND


class WebsiteHelpdesk(http.Controller):

    @http.route(['/helpdesk/rating', '/helpdesk/rating/<model("helpdesk.team"):team>'], type='http', auth="public", website=True, sitemap=False)
    def page(self, team=False, **kw):
        # to avoid giving any access rights on helpdesk team to the public user, let's use sudo
        # and check if the user should be able to view the team (team managers only if it's not published or has no rating)
        user = request.env.user
        team_domain = [('id', '=', team.id)] if team else []
        if user.has_group('helpdesk.group_heldpesk_manager'):
            domain = AND([[('use_rating', '=', True)], team_domain])
        else:
            domain = AND([[('use_rating', '=', True), ('portal_show_rating', '=', True)], team_domain])
        teams = request.env['helpdesk.team'].search(domain)
        team_values = []
        for team in teams:
            tickets = request.env['helpdesk.ticket'].sudo().search([('team_id', '=', team.id)])
            domain = [
                ('res_model', '=', 'helpdesk.ticket'), ('res_id', 'in', tickets.ids),
                ('consumed', '=', True), ('rating', '>=', 1),
            ]
            ratings = request.env['rating.rating'].sudo().search(domain, order="id desc", limit=100)

            yesterday = (datetime.date.today()-datetime.timedelta(days=-1)).strftime('%Y-%m-%d 23:59:59')
            stats = {}
            any_rating = False
            for x in (7, 30, 90):
                todate = (datetime.date.today()-datetime.timedelta(days=x)).strftime('%Y-%m-%d 00:00:00')
                domdate = domain + [('create_date', '<=', yesterday), ('create_date', '>=', todate)]
                stats[x] = {1: 0, 3: 0, 5: 0}
                rating_stats = request.env['rating.rating'].sudo()._read_group(domdate, ['rating'], ['__count'])
                total = sum(count for __, count in rating_stats)
                for rating, count in rating_stats:
                    any_rating = True
                    stats[x][rating] = (count * 100) / total
            values = {
                'team': team,
                'ratings': ratings if any_rating else False,
                'stats': stats,
                'is_helpdesk_user': user.has_group('helpdesk.group_helpdesk_user')
            }
            team_values.append(values)
        return request.render('helpdesk.team_rating_page', {'page_name': 'rating', 'teams': team_values})
