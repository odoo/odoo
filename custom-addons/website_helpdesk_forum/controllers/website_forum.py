# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import route, request
from odoo.osv import expression
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.website_forum.controllers.website_forum import WebsiteForum


class WebsiteForumHelpdesk(WebsiteForum):

    @route('/helpdesk/<model("helpdesk.team"):team>/forums', type='http', auth="public", website=True, sitemap=True)
    def helpdesk_forums(self, team=None):
        if not team or not team.website_forum_ids:
            return request.redirect('/forum')
        domain = expression.AND([request.website.website_domain(), [('id', 'in', team.website_forum_ids.ids)]])
        forums = request.env['forum.forum'].search(domain)
        if len(forums) == 1:
            return request.redirect('/forum/%s' % slug(forums[0]), code=302)
        return request.render(self.get_template_xml_id(), {
            'forums': forums
        })

    def get_template_xml_id(self):
        return "website_helpdesk_forum.forum_all"
