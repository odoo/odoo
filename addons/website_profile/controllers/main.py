# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import werkzeug.exceptions
import werkzeug.urls
import werkzeug.wrappers

from odoo import http, modules
from odoo.http import request


class WebsiteProfile(http.Controller):

    def _get_notifications(self):
        badge_subtype = request.env.ref('gamification.mt_badge_granted')
        if badge_subtype:
            msg = request.env['mail.message'].search([('subtype_id', '=', badge_subtype.id), ('needaction', '=', True)])
        else:
            msg = list()
        return msg

    def _prepare_user_values(self, **kwargs):
        values = {
            'user': request.env.user,
            'is_public_user': request.env.user.id == request.website.user_id.id,
            'notifications': self._get_notifications(),
            'header': kwargs.get('header', dict()),
            'searches': kwargs.get('searches', dict()),
            'validation_email_sent': request.session.get('validation_email_sent', False),
            'validation_email_done': request.session.get('validation_email_done', False),
        }
        values.update(kwargs)
        return values

    def _prepare_save_edited_profile_values(self, user, **kwargs):
        values = {
            'name': kwargs.get('name'),
            'website': kwargs.get('website'),
            'email': kwargs.get('email'),
            'city': kwargs.get('city'),
            'country_id': int(kwargs.get('country')) if kwargs.get('country') else False,
            'website_description': kwargs.get('description'),
        }

        if 'clear_image' in kwargs:
            values['image'] = False
        elif kwargs.get('ufile'):
            image = kwargs.get('ufile').read()
            values['image'] = base64.b64encode(image)

        if request.uid == user.id:  # the controller allows to edit only its own privacy settings; use partner management for other cases
            values['website_published'] = kwargs.get('website_published') == 'True'
        return values

    @http.route(['/profile/user/<int:user_id>'], type='http', auth="public", website=True)
    def open_user(self, user_id=0, **post):
        # isn't that a security hole ?
        user = request.env['res.users'].sudo().browse(user_id)
        values = {
            'uid': request.env.user.id,
            'user': user,
            'main_object': user,
            'is_profile_page': True,
        }
        return request.render("website_profile.user_detail_main", values)

    @http.route('/profile/edit', type='http', auth="user", website=True)
    def edit_profile(self, **kwargs):
        countries = request.env['res.country'].search([])
        values = self._prepare_user_values(searches=kwargs)
        values.update({
            'email_required': kwargs.get('email_required'),
            'countries': countries,
            'notifications': self._get_notifications(),
        })
        return request.render("website_profile.edit_profile_main", values)

    @http.route('/profile/user/<model("res.users"):user>/save', type='http', auth="user", methods=['POST'], website=True)
    def save_edited_profile(self, user, **kwargs):
        values = self._prepare_save_edited_profile_values(user, **kwargs)
        user.write(values)
        return werkzeug.utils.redirect("/profile/user/%d" % user.id)

    @http.route('/profile/ranks', type='http', auth="public", website=True)
    def ranks(self, **searches):
        Rank = request.env['gamification.karma.rank']
        ranks = Rank.sudo().search([])
        ranks = sorted(ranks, key=lambda b: b.karma_min)
        values = {
            'ranks': ranks,
        }
        return request.render("website_profile.rank_main", values)

    # Pas sur que ca doit rester ici.. on devrait filtrer sur les badge liés à quelque chose (comme le forum)
    @http.route('/profile/badge', type='http', auth="public", website=True)
    def badges(self, **searches):
        Badge = request.env['gamification.badge']
        badges = Badge.sudo().search([])
        # badges = Badge.sudo().search([('challenge_ids.category', '=', 'forum')])
        badges = sorted(badges, key=lambda b: b.stat_count_distinct, reverse=True)
        values = self._prepare_user_values(searches={'badges': True})
        values.update({
            'badges': badges,
        })
        return request.render("website_profile.badge_main", values)
