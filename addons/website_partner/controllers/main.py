# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo.addons.website.models.website import unslug


class WebsitePartnerPage(http.Controller):

    # Do not use semantic controller due to SUPERUSER_ID
    @http.route(['/partners/<partner_id>'], type='http', auth="public", website=True)
    def partners_detail(self, partner_id, **post):
        _, partner_id = unslug(partner_id)
        if partner_id:
            partner_sudo = request.env['res.partner'].sudo().browse(partner_id)
            is_website_publisher = request.env['res.users'].has_group('website.group_website_publisher')
            if partner_sudo.exists() and (partner_sudo.website_published or is_website_publisher):
                values = {
                    'main_object': partner_sudo,
                    'partner': partner_sudo,
                    'edit_page': False
                }
                return request.render("website_partner.partner_page", values)
        return request.not_found()
