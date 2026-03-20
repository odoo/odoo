# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request


class WebsitePartnerPage(http.Controller):

    def _get_partners_detail_values(self, partner_id, **post):
        partner_sudo = request.env['res.partner'].sudo().browse(partner_id)
        return {
            'main_object': partner_sudo,
            'partner': partner_sudo,
            'edit_page': False
        }

    # Do not use semantic controller due to SUPERUSER_ID
    @http.route(['/partners/<partner_id>'], type='http', auth="public", website=True)
    def partners_detail(self, partner_id, **post):
        current_slug = partner_id
        _, partner_id = request.env['ir.http']._unslug(partner_id)
        if partner_id:
            partner_sudo = request.env['res.partner'].sudo().browse(partner_id)
            is_website_restricted_editor = request.env.user.has_group('website.group_website_restricted_editor')
            if partner_sudo.exists() and (partner_sudo.website_published or is_website_restricted_editor):
                partner_slug = request.env['ir.http']._slug(partner_sudo)
                if partner_slug != current_slug:
                    return request.redirect('/partners/%s' % partner_slug)
                values = self._get_partners_detail_values(partner_id, **post)
                return request.render("website_partner.partner_page", values)
        raise request.not_found()
