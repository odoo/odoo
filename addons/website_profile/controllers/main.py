# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import werkzeug
import werkzeug.exceptions
import werkzeug.urls
import werkzeug.wrappers

from odoo import http, modules, tools
from odoo.http import request
from odoo.osv import expression
from odoo.tools import limited_image_resize


class WebsiteProfile(http.Controller):

    # Profile
    # ---------------------------------------------------

    def _check_avatar_access(self, user_id, **post):
        """ Base condition to see user avatar independently form access rights
        is to see published users having karma, meaning they participated to
        frontend applications like forum or elearning. """
        try:
            user = request.env['res.users'].sudo().browse(user_id).exists()
        except:
            return False
        if user:
            return user.website_published and user.karma > 0
        return False

    def _check_user_profile_access(self, user_id):
        user_sudo = request.env['res.users'].sudo().browse(user_id)
        if user_sudo.karma == 0 or not user_sudo.website_published or \
            (user_sudo.id != request.session.uid and request.env.user.karma < request.website.karma_profile_min):
            return False
        return user_sudo

    def _prepare_user_values(self, **kwargs):
        values = {
            'user': request.env.user,
            'is_public_user': request.website.is_public_user(),
        }
        values.update(kwargs)
        return values

    def _prepare_user_profile_parameters(self, **post):
        return post

    def _prepare_user_profile_values(self, user, **post):
        return {
            'uid': request.env.user.id,
            'user': user,
            'main_object': user,
            'is_profile_page': True,
            'edit_button_url_param': '',
        }

    @http.route([
        '/profile/avatar/<int:user_id>',
    ], type='http', auth="public", website=True, sitemap=False)
    def get_user_profile_avatar(self, user_id=0, width=0, height=0, crop=False, avoid_if_small=False, upper_limit=False, **post):
        can_sudo = self._check_avatar_access(user_id, **post)
        fname = post.get('field', 'image_medium')
        if can_sudo:
            status, headers, content = request.env['ir.http'].sudo().binary_content(
                model='res.users', id=user_id, field=fname,
                default_mimetype='image/png')
        else:
            status, headers, content = request.env['ir.http'].binary_content(
                model='res.users', id=user_id, field=fname,
                default_mimetype='image/png')
        if status == 301:
            return request.env['ir.http']._response_by_status(status, headers, content)
        if status == 304:
            return werkzeug.wrappers.Response(status=304)

        if not content:
            img_path = modules.get_module_resource('web', 'static/src/img', 'placeholder.png')
            with open(img_path, 'rb') as f:
                image = f.read()
            content = base64.b64encode(image)
            dictheaders = dict(headers) if headers else {}
            dictheaders['Content-Type'] = 'image/png'
            headers = list(dictheaders.items())
            if not (width or height):
                suffix = fname.split('_')[-1]
                if suffix in ('small', 'medium', 'big'):
                    content = getattr(tools, 'image_resize_image_%s' % suffix)(content)

        content = limited_image_resize(
            content, width=width, height=height, crop=crop, upper_limit=upper_limit, avoid_if_small=avoid_if_small)

        image_base64 = base64.b64decode(content)
        headers.append(('Content-Length', len(image_base64)))
        response = request.make_response(image_base64, headers)
        response.status_code = status
        return response

    @http.route(['/profile/user/<int:user_id>'], type='http', auth="public", website=True)
    def view_user_profile(self, user_id, **post):
        user = self._check_user_profile_access(user_id)
        if not user:
            return request.render("website_profile.private_profile")
        params = self._prepare_user_profile_parameters(**post)
        values = self._prepare_user_profile_values(user, **params)
        return request.render("website_profile.user_profile_main", values)

    # Edit Profile
    # ---------------------------------------------------
    @http.route('/profile/edit', type='http', auth="user", website=True)
    def view_user_profile_edition(self, **kwargs):
        countries = request.env['res.country'].search([])
        values = self._prepare_user_values(searches=kwargs)
        values.update({
            'email_required': kwargs.get('email_required'),
            'countries': countries,
            'url_param': kwargs.get('url_param'),
        })
        return request.render("website_profile.user_profile_edit_main", values)

    def _profile_edition_preprocess_values(self, user, **kwargs):
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

    @http.route('/profile/user/save', type='http', auth="user", methods=['POST'], website=True)
    def save_edited_profile(self, **kwargs):
        user = request.env.user
        values = self._profile_edition_preprocess_values(user, **kwargs)
        whitelisted_values = {key: values[key] for key in type(user).SELF_WRITEABLE_FIELDS if key in values}
        user.write(whitelisted_values)
        if kwargs.get('url_param'):
            return werkzeug.utils.redirect("/profile/user/%d?%s" % (user.id, kwargs['url_param']))
        else:
            return werkzeug.utils.redirect("/profile/user/%d" % user.id)
    # Ranks
    # ---------------------------------------------------
    @http.route('/profile/ranks', type='http', auth="public", website=True)
    def ranks(self, **kwargs):
        Rank = request.env['gamification.karma.rank']
        ranks = Rank.sudo().search([])
        ranks = ranks.sorted(key=lambda b: b.karma_min)
        values = {
            'ranks': ranks,
        }
        return request.render("website_profile.rank_main", values)

    # Badges
    # ---------------------------------------------------
    def _prepare_badges_domain(self, **kwargs):
        """
        Hook for other modules to restrict the badges showed on profile page, depending of the context
        """
        domain = [('website_published', '=', True)]
        if 'category' in kwargs:
            domain = expression.AND([[('challenge_ids.category', '=', kwargs.get('category'))], domain])
        return domain

    @http.route('/profile/badge', type='http', auth="public", website=True)
    def badges(self, **kwargs):
        Badge = request.env['gamification.badge']
        badges = Badge.sudo().search(self._prepare_badges_domain(**kwargs))
        badges = sorted(badges, key=lambda b: b.stat_count_distinct, reverse=True)
        values = self._prepare_user_values(searches={'badges': True})
        values.update({
            'badges': badges,
        })
        return request.render("website_profile.badge_main", values)
