# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, tools, SUPERUSER_ID
from odoo.http import request

from odoo.addons.im_livechat.controllers.main import LivechatController


class LivechatController(LivechatController):

    @http.route('/im_livechat/load_templates', type='json', auth='none', cors="*")
    def load_templates(self, **kwargs):
        res = super(LivechatController, self).load_templates(**kwargs)
        if request.env['res.users'].with_user(SUPERUSER_ID).has_group('crm_livechat.group_generate_lead'):
            res.append(tools.file_open('crm_livechat/static/src/xml/im_livechat.xml', 'rb').read())
        return res


class CrmController(http.Controller):

    @http.route(['/livechat/generate_lead', '/livechat/update_lead_description'], type='json', auth="public", website=True)
    def generate_lead(self, name=False, email_from=False, description='', lead_id=False, channel_uuid=None):
        Channel = request.env['mail.channel']
        channel = channel_uuid and Channel.with_user(SUPERUSER_ID).search([('uuid', '=', channel_uuid)])
        if channel:
            if lead_id:
                lead = request.env['crm.lead'].sudo().browse(lead_id)
                lead.description += "\n" + description
            else:
                return channel.generate_lead(name, email_from)
        elif request.env['website.visitor']._get_visitor_from_request():
            return Channel.with_user(SUPERUSER_ID).generate_lead(name, email_from, description)
