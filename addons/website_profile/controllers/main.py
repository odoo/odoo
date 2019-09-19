# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import werkzeug
import werkzeug.exceptions
import werkzeug.urls
import werkzeug.wrappers
import math

from odoo import http, modules, tools
from odoo.http import request
from odoo.osv import expression


class WebsiteProfile(http.Controller):
    _users_per_page = 30
    _pager_max_pages = 5

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

    def _get_default_avatar(self):
        img_path = modules.get_module_resource('web', 'static/src/img', 'placeholder.png')
        with open(img_path, 'rb') as f:
            return base64.b64encode(f.read())

    def _check_user_profile_access(self, user_id):
        user_sudo = request.env['res.users'].sudo().browse(user_id)
        # User can access - no matter what - his own profile
        if user_sudo.id == request.env.user.id:
            return user_sudo
        if user_sudo.karma == 0 or not user_sudo.website_published or \
            (user_sudo.id != request.session.uid and request.env.user.karma < request.website.karma_profile_min):
            return False
        return user_sudo

    def _prepare_user_values(self, **kwargs):
        values = {
            'user': request.env.user,
            'is_public_user': request.website.is_public_user(),
            'validation_email_sent': request.session.get('validation_email_sent', False),
            'validation_email_done': request.session.get('validation_email_done', False),
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
    def get_user_profile_avatar(self, user_id, field='image_256', width=0, height=0, crop=False, **post):
        if field not in ('image_128', 'image_256'):
            return werkzeug.exceptions.Forbidden()

        can_sudo = self._check_avatar_access(user_id, **post)
        if can_sudo:
            status, headers, image_base64 = request.env['ir.http'].sudo().binary_content(
                model='res.users', id=user_id, field=field,
                default_mimetype='image/png')
        else:
            status, headers, image_base64 = request.env['ir.http'].binary_content(
                model='res.users', id=user_id, field=field,
                default_mimetype='image/png')
        if status == 301:
            return request.env['ir.http']._response_by_status(status, headers, image_base64)
        if status == 304:
            return werkzeug.wrappers.Response(status=304)

        if not image_base64:
            image_base64 = self._get_default_avatar()
            if not (width or height):
                width, height = tools.image_guess_size_from_field_name(field)

        image_base64 = tools.image_process(image_base64, size=(int(width), int(height)), crop=crop)

        content = base64.b64decode(image_base64)
        headers = http.set_safe_image_headers(headers, content)
        response = request.make_response(content, headers)
        response.status_code = status
        return response

    @http.route(['/profile/user/<int:user_id>'], type='http', auth="public", website=True)
    def view_user_profile(self, user_id, **post):
        user = self._check_user_profile_access(user_id)
        if not user:
            return request.render("website_profile.private_profile")
        values = self._prepare_user_values(**post)
        params = self._prepare_user_profile_parameters(**post)
        values.update(self._prepare_user_profile_values(user, **params))
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
            values['image_1920'] = False
        elif kwargs.get('ufile'):
            image = kwargs.get('ufile').read()
            values['image_1920'] = base64.b64encode(image)

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

    # Ranks and Badges
    # ---------------------------------------------------
    def _prepare_badges_domain(self, **kwargs):
        """
        Hook for other modules to restrict the badges showed on profile page, depending of the context
        """
        domain = [('website_published', '=', True)]
        if 'badge_category' in kwargs:
            domain = expression.AND([[('challenge_ids.category', '=', kwargs.get('badge_category'))], domain])
        return domain

    @http.route('/profile/ranks_badges', type='http', auth="public", website=True)
    def view_ranks_badges(self, **kwargs):
        ranks = []
        if 'badge_category' not in kwargs:
            Rank = request.env['gamification.karma.rank']
            ranks = Rank.sudo().search([], order='karma_min DESC')

        Badge = request.env['gamification.badge']
        badges = Badge.sudo().search(self._prepare_badges_domain(**kwargs))
        badges = sorted(badges, key=lambda b: b.stat_count_distinct, reverse=True)
        values = self._prepare_user_values(searches={'badges': True})

        values.update({
            'ranks': ranks,
            'badges': badges,
            'user': request.env.user,
        })
        return request.render("website_profile.rank_badge_main", values)

    # All Users Page
    # ---------------------------------------------------
    def _prepare_all_users_values(self, users):
        user_values = []
        for user in users:
            user_values.append({
                'id': user.id,
                'name': user.name,
                'company_name': user.company_id.name,
                'rank': user.rank_id.name,
                'karma': user.karma,
                'badge_count': len(user.badge_ids),
                'website_published': user.website_published
            })
        return user_values

    @http.route(['/profile/users',
                 '/profile/users/page/<int:page>'], type='http', auth="public", website=True)
    def view_all_users_page(self, page=1, **searches):
        User = request.env['res.users']
        dom = [('karma', '>', 1), ('website_published', '=', True)]

        # Searches
        search_term = searches.get('search')
        if search_term:
            dom = expression.AND([['|', ('name', 'ilike', search_term), ('company_id.name', 'ilike', search_term)], dom])

        user_count = User.sudo().search_count(dom)

        if user_count:
            page_count = math.ceil(user_count / self._users_per_page)
            pager = request.website.pager(url="/profile/users", total=user_count, page=page, step=self._users_per_page,
                                          scope=page_count if page_count < self._pager_max_pages else self._pager_max_pages)

            users = User.sudo().search(dom, limit=self._users_per_page, offset=pager['offset'], order='karma DESC')
            user_values = self._prepare_all_users_values(users)

            # Get karma position for users (only website_published)
            position_domain = [('karma', '>', 1), ('website_published', '=', True)]
            position_map = self._get_users_karma_position(position_domain, users.ids)
            for user in user_values:
                user['position'] = position_map.get(user['id'], 0)

            values = {
                'top3_users': user_values[:3] if not search_term and page == 1 else None,
                'users': user_values[3:] if not search_term and page == 1 else user_values,
                'pager': pager
            }
        else:
            values = {'top3_users': [], 'users': [], 'search': search_term, 'pager': dict(page_count=0)}

        return request.render("website_profile.users_page_main", values)

    def _get_users_karma_position(self, domain, user_ids):
        if not user_ids:
            return {}

        Users = request.env['res.users']
        where_query = Users._where_calc(domain)
        from_clause, where_clause, where_clause_params = where_query.get_sql()

        # we search on every user in the DB to get the real positioning (not the one inside the subset)
        # then, we filter to get only the subset.
        query = """
            SELECT sub.id, sub.karma_position
            FROM (
                SELECT "res_users"."id", row_number() OVER (ORDER BY res_users.karma DESC) AS karma_position
                FROM {from_clause}
                WHERE {where_clause}
            ) sub
            WHERE sub.id IN %s
            """.format(from_clause=from_clause, where_clause=where_clause)

        request.env.cr.execute(query, where_clause_params + [tuple(user_ids)])

        return {item['id']: item['karma_position'] for item in request.env.cr.dictfetchall()}

    # User and validation
    # --------------------------------------------------

    @http.route('/profile/send_validation_email', type='json', auth='user', website=True)
    def send_validation_email(self, **kwargs):
        if request.env.uid != request.website.user_id.id:
            request.env.user._send_profile_validation_email(**kwargs)
        request.session['validation_email_sent'] = True
        return True

    @http.route('/profile/validate_email', type='http', auth='public', website=True, sitemap=False)
    def validate_email(self, token, user_id, email, **kwargs):
        done = request.env['res.users'].sudo().browse(int(user_id))._process_profile_validation_token(token, email)
        if done:
            request.session['validation_email_done'] = True
        url = kwargs.get('redirect_url', '/')
        return request.redirect(url)

    @http.route('/profile/validate_email/close', type='json', auth='public', website=True)
    def validate_email_done(self, **kwargs):
        request.session['validation_email_done'] = False
        return True
