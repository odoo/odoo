# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urllib.parse import urlsplit
import werkzeug
import werkzeug.exceptions
import werkzeug.urls
import werkzeug.wrappers
import math

from dateutil.relativedelta import relativedelta
from operator import itemgetter

from odoo import _, fields, http, tools
from odoo.fields import Domain
from odoo.http import request
from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)


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

    def _check_user_profile_access(self, user_id):
        """ Takes a user_id and returns:
            - (user record, False) when the user is granted access
            - (False, str) when the user is denied access
            Raises a Not Found Exception when the profile does not exist
        """
        user_sudo = request.env['res.users'].sudo().browse(user_id)
        # User can access - no matter what - his own profile
        if user_sudo.id == request.env.user.id:
            return user_sudo, False

        # Profile being published is more specific than general karma requirement (check it first!)
        if not user_sudo.website_published:
            return False, _('This profile is private!')
        elif not user_sudo.exists():
            raise request.not_found()

        elif request.env.user.karma < request.website.karma_profile_min:
            return False, _("Not have enough karma to view other users' profile.")
        return user_sudo, False

    def _prepare_user_values(self, **kwargs):
        kwargs.pop('edit_translations', None) # avoid nuking edit_translations
        values = {
            'user': request.env.user,
            'is_public_user': request.website.is_public_user(),
            'validation_email_sent': request.session.get('validation_email_sent', False),
            'validation_email_done': request.session.get('validation_email_done', False),
        }
        return values

    def _prepare_user_profile_parameters(self, **post):
        return post

    def _prepare_user_profile_values(self, user, **post):
        return {
            'uid': request.env.user.id,
            'user': user,
            'main_object': user,
            'is_profile_page': True,
        }

    @http.route([
        '/profile/avatar/<int:user_id>',
    ], type='http', auth="public", website=True, sitemap=False, readonly=True)
    def get_user_profile_avatar(self, user_id, field='avatar_256', width=0, height=0, crop=False, **post):
        if field not in ('image_128', 'image_256', 'avatar_128', 'avatar_256'):
            return werkzeug.exceptions.Forbidden()

        if (int(width), int(height)) == (0, 0):
            width, height = tools.image.image_guess_size_from_field_name(field)

        can_sudo = self._check_avatar_access(int(user_id), **post)
        return request.env['ir.binary']._get_image_stream_from(
            request.env['res.users'].sudo(can_sudo).browse(int(user_id)),
            field_name=field, width=int(width), height=int(height), crop=crop
        ).get_response()

    def _prepare_url_from_info(self):
        url_from = request.httprequest.headers.get('Referer')
        url_current = request.httprequest.url
        void_from_url = {'url_from_label': None, 'url_from': None}
        if url_from and ((url_from_parsed := urlsplit(url_from)).netloc == urlsplit(url_current).netloc):
            path = url_from_parsed.path
            return next(
                (
                    {'url_from_label': label, 'url_from': url_from}
                    for prefix, label in (('forum', _('Forum')), ('slides', _('All Courses')))
                    if path == f'/{prefix}' or path.startswith(f'/{prefix}/')
                ), void_from_url)
        return void_from_url

    @http.route('/profile/user/<int:user_id>', type='http', auth='public', website=True, readonly=True)
    def view_user_profile(self, user_id, **post):
        user_sudo, denial_reason = self._check_user_profile_access(user_id)
        if denial_reason:
            return request.render('website_profile.profile_access_denied', {'denial_reason': denial_reason})
        params = self._prepare_user_profile_parameters(**post)
        values = {
            **self._prepare_user_values(**post),
            **self._prepare_user_profile_values(user_sudo, **params),
            **self._prepare_url_from_info(),
        }
        return request.render("website_profile.user_profile_main", values)

    # Edit Profile
    # ---------------------------------------------------
    def _profile_edition_preprocess_values(self, user, **kwargs):
        values = {
            'name': kwargs.get('name'),
            'website': kwargs.get('website'),
            'email': kwargs.get('email'),
            'city': kwargs.get('city'),
            'country_id': kwargs.get('country_id'),
            'website_description': kwargs.get('website_description'),
        }

        if 'image_1920' in kwargs:
            values['image_1920'] = kwargs.get('image_1920')

        if request.env.uid == user.id:  # the controller allows to edit only its own privacy settings; use partner management for other cases
            values['website_published'] = kwargs.get('website_published')
        return values

    @http.route('/profile/user/save', type='jsonrpc', auth='user', methods=['POST'], website=True)
    def save_edited_profile(self, **kwargs):
        user_id = int(kwargs.get('user_id', 0))
        user = request.env['res.users'].browse(user_id or request.env.uid)
        values = self._profile_edition_preprocess_values(user, **kwargs)
        user.write(values)

    # Ranks and Badges
    # ---------------------------------------------------
    def _prepare_badges_domain(self, **kwargs):
        """
        Hook for other modules to restrict the badges showed on profile page, depending of the context
        """
        domain = Domain('website_published', '=', True)
        if 'badge_category' in kwargs:
            domain = Domain('challenge_ids.challenge_category', '=', kwargs.get('badge_category')) & domain
        return domain

    def _prepare_ranks_badges_values(self, **kwargs):
        ranks = []
        if 'badge_category' not in kwargs:
            Rank = request.env['gamification.karma.rank']
            ranks = Rank.sudo().search([], order='karma_min DESC')

        Badge = request.env['gamification.badge']
        badges = Badge.sudo().search(self._prepare_badges_domain(**kwargs))
        badges = badges.sorted("granted_users_count", reverse=True)
        values = self._prepare_user_values(searches={'badges': True})

        values.update({
            'ranks': ranks,
            'badges': badges,
            'user': request.env.user,
        })
        return values

    @http.route('/profile/ranks_badges', type='http', auth="public", website=True, sitemap=True, readonly=True, list_as_website_content=_lt("Ranks and Badges"))
    def view_ranks_badges(self, **kwargs):
        values = {
            **self._prepare_ranks_badges_values(**kwargs),
            **self._prepare_url_from_info(),
        }
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
                 '/profile/users/page/<int:page>'], type='http', auth="public", website=True, sitemap=True, readonly=True, list_as_website_content=_lt("User Profiles"))
    def view_all_users_page(self, page=1, **kwargs):
        User = request.env['res.users']
        dom = [('karma', '>', 1), ('website_published', '=', True)]

        # Searches
        search_term = kwargs.get('search')
        group_by = kwargs.get('group_by', False)
        render_values = {
            'search': search_term,
            'group_by': group_by or 'all',
        }
        if search_term:
            dom = Domain.AND([['|', ('name', 'ilike', search_term), ('partner_id.commercial_company_name', 'ilike', search_term)], dom])

        user_count = User.sudo().search_count(dom)
        my_user = request.env.user
        current_user_value = False
        user_values = []
        pager = {'page_count': 0}
        if user_count:
            page_count = math.ceil(user_count / self._users_per_page)
            pager = request.website.pager(url="/profile/users", total=user_count, page=page, step=self._users_per_page,
                                          scope=page_count if page_count < self._pager_max_pages else self._pager_max_pages,
                                          url_args=kwargs)
            position_map = self._get_position_map(
                dom,
                group_by=group_by,
                page=page,
                limit=self._users_per_page
            )

            user_ids_with_ranking = list(position_map.keys())

            if user_ids_with_ranking:

                user_values = self._prepare_all_users_values(User.sudo().browse(user_ids_with_ranking))
                for user_dict in user_values:
                    user_id = user_dict['id']
                    rank_data = position_map.get(user_id, {})

                    user_dict['position'] = rank_data.get('karma_position', 0)
                    user_dict['karma_gain'] = rank_data.get('karma_gain_total', 0)

                user_values.sort(key=lambda x: x['position'])

            if my_user.website_published and my_user.karma and my_user.id not in user_ids_with_ranking:
                my_user_map = self._get_position_map(
                    dom,
                    group_by=group_by,
                    target_user_id=my_user.id,
                )

                if my_user.id in my_user_map:
                    current_user_value = self._prepare_all_users_values(my_user.sudo())[0]

                    current_user_value['position'] = my_user_map[my_user.id].get('karma_position', 0)
                    current_user_value['karma_gain'] = my_user_map[my_user.id].get('karma_gain_total', 0)

        render_values.update({
            'top3_users': user_values[:3] if not search_term and page == 1 else [],
            'users': user_values,
            'my_user': current_user_value,
            'pager': pager,
            **self._prepare_url_from_info(),
        })
        return request.render("website_profile.users_page_main", render_values)

    def _get_position_map(self, domain, group_by, page=1, limit=20, target_user_id=None):
        """ Switcher: Decides between fast ORM ranking (All time) vs Slow SQL ranking (Time range) """
        User = request.env['res.users']
        offset = (page - 1) * limit

        if group_by in ('week', 'month'):
            to_date = fields.Date.today()
            if group_by == 'week':
                from_date = to_date - relativedelta(weeks=1)
            elif group_by == 'month':
                from_date = to_date - relativedelta(months=1)

            position_results = User._get_tracking_karma_gain_position(
                user_domain=domain,
                from_date=from_date,
                to_date=to_date,
                limit=limit,
                offset=offset,
                target_user_id=target_user_id,
                )
            return {res['user_id']: res for res in position_results}

        else:
            position_results = User._get_karma_position(
                user_domain=domain,
                limit=limit,
                offset=offset,
                target_user_id=target_user_id,
            )

            return {res['user_id']: res for res in position_results}

    # User and validation
    # --------------------------------------------------

    @http.route('/profile/send_validation_email', type='jsonrpc', auth='user', website=True)
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

    @http.route('/profile/validate_email/close', type='jsonrpc', auth='public', website=True)
    def validate_email_done(self, **kwargs):
        request.session['validation_email_done'] = False
        request.session['validation_email_sent'] = False
        return True
