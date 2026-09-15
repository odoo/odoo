import math
from operator import itemgetter
from urllib.parse import urlsplit

import werkzeug.exceptions
from dateutil.relativedelta import relativedelta

from odoo import _, fields, http, tools
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.http import request
from odoo.libs.debug_log import DebugLog
from odoo.tools.translate import LazyTranslate

_debug = DebugLog(__name__)

_lt = LazyTranslate(__name__)


class WebsiteProfile(http.Controller):
    _users_per_page = 30
    _pager_max_pages = 5

    def _check_avatar_access(self, user_id, **post):
        try:
            user = request.env["res.users"].sudo().browse(user_id).exists()
        except Exception:
            return False
        if user:
            return user.website_published and user.karma > 0
        return False

    def _check_user_profile_access(self, user_id):
        user_sudo = request.env["res.users"].sudo().browse(user_id)
        if not user_sudo.exists():
            raise request.prepare_not_found_error()

        if user_sudo.id == request.env.user.id:
            return user_sudo, False

        if not user_sudo.website_published:
            _debug.logic("profile_refused", reason="private", user=user_id)
            return False, _("This profile is private!")
        elif request.env.user.karma < request.website.karma_profile_min:
            _debug.logic(
                "profile_refused",
                reason="karma",
                user=user_id,
                required=request.website.karma_profile_min,
            )
            return False, _("Not have enough karma to view other users' profile.")
        return user_sudo, False

    def _prepare_user_values(self, **kwargs):
        kwargs.pop("edit_translations", None)
        return {
            "user": request.env.user,
            "is_public_user": request.website.is_public_user(),
            "validation_email_sent": request.session.get(
                "validation_email_sent", False
            ),
            "validation_email_done": request.session.get(
                "validation_email_done", False
            ),
        }

    def _prepare_user_profile_parameters(self, **post):
        return post

    def _prepare_user_profile_values(self, user, **post):
        return {
            "uid": request.env.user.id,
            "user": user,
            "main_object": user,
            "is_profile_page": True,
        }

    @http.route(
        [
            "/profile/avatar/<int:user_id>",
        ],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
        readonly=True,
    )
    def get_user_profile_avatar(
        self, user_id, field="avatar_256", width=0, height=0, crop=False, **post
    ):
        if field not in ("image_128", "image_256", "avatar_128", "avatar_256"):
            return werkzeug.exceptions.Forbidden()

        if (int(width), int(height)) == (0, 0):
            width, height = tools.image.image_guess_size_from_field_name(field)

        can_sudo = self._check_avatar_access(int(user_id), **post)
        return (
            request.env["ir.binary"]
            ._get_stream_image_from_record(
                request.env["res.users"].sudo(can_sudo).browse(int(user_id)),
                field_name=field,
                width=int(width),
                height=int(height),
                crop=crop,
            )
            .prepare_response()
        )

    def _prepare_url_from_info(self):
        url_from = request.httprequest.headers.get("Referer")
        url_current = request.httprequest.url
        void_from_url = {"url_from_label": None, "url_from": None}
        if url_from and (
            (url_from_parsed := urlsplit(url_from)).netloc
            == urlsplit(url_current).netloc
        ):
            path = url_from_parsed.path
            return next(
                (
                    {"url_from_label": label, "url_from": url_from}
                    for prefix, label in (
                        ("forum", _("Forum")),
                        ("slides", _("All Courses")),
                    )
                    if path == f"/{prefix}" or path.startswith(f"/{prefix}/")
                ),
                void_from_url,
            )
        return void_from_url

    @http.route(
        "/profile/user/<int:user_id>",
        type="http",
        auth="public",
        website=True,
        readonly=True,
    )
    def view_user_profile(self, user_id, **post):
        user_sudo, denial_reason = self._check_user_profile_access(user_id)
        if denial_reason:
            return request.render(
                "website_profile.profile_access_denied",
                {"denial_reason": denial_reason},
            )
        params = self._prepare_user_profile_parameters(**post)
        values = {
            **self._prepare_user_values(**post),
            **self._prepare_user_profile_values(user_sudo, **params),
            **self._prepare_url_from_info(),
        }
        return request.render("website_profile.user_profile_main", values)

    def _profile_edition_preprocess_values(self, user, **kwargs):
        values = {
            "name": kwargs.get("name"),
            "website": kwargs.get("website"),
            "email": kwargs.get("email"),
            "city": kwargs.get("city"),
            "country_id": kwargs.get("country_id"),
            "website_description": kwargs.get("website_description"),
        }

        if "image_1920" in kwargs:
            values["image_1920"] = kwargs.get("image_1920")

        if request.env.uid == user.id:
            values["website_published"] = kwargs.get("website_published")
        return values

    @http.route(
        "/profile/user/save",
        type="jsonrpc",
        auth="user",
        methods=["POST"],
        website=True,
    )
    def save_edited_profile(self, **kwargs):
        user_id = int(kwargs.get("user_id", 0))
        if user_id and request.env.user.id != user_id and request.env.user._is_admin():
            user = request.env["res.users"].browse(user_id)
        else:
            user = request.env.user
        values = self._profile_edition_preprocess_values(user, **kwargs)
        whitelisted_values = {
            key: values[key]
            for key in sorted(user._get_self_accessible_fields()[1])
            if key in values
        }
        if (
            not user.partner_id._can_edit_country()
            and whitelisted_values.get("country_id") != user.partner_id.country_id.id
        ):
            raise UserError(
                _(
                    "Changing the country is not allowed once document(s) have been issued for your account. Please contact us directly for this operation."
                )
            )
        user.write(whitelisted_values)

    def _get_domain_badges(self, **kwargs):
        domain = Domain("website_published", "=", True)
        if "badge_category" in kwargs:
            domain = (
                Domain(
                    "challenge_ids.challenge_category",
                    "=",
                    kwargs.get("badge_category"),
                )
                & domain
            )
        return domain

    def _prepare_ranks_badges_values(self, **kwargs):
        ranks = []
        if "badge_category" not in kwargs:
            Rank = request.env["gamification.karma.rank"]
            ranks = Rank.sudo().search([], order="karma_min DESC")

        Badge = request.env["gamification.badge"]
        badges = Badge.sudo().search(self._get_domain_badges(**kwargs))
        badges = badges.sorted("granted_users_count", reverse=True)
        values = self._prepare_user_values(searches={"badges": True})

        values.update(
            {
                "ranks": ranks,
                "badges": badges,
                "user": request.env.user,
            }
        )
        return values

    @http.route(
        "/profile/ranks_badges",
        type="http",
        auth="public",
        website=True,
        sitemap=True,
        readonly=True,
        list_as_website_content=_lt("Ranks and Badges"),
    )
    def view_ranks_badges(self, **kwargs):
        values = {
            **self._prepare_ranks_badges_values(**kwargs),
            **self._prepare_url_from_info(),
        }
        return request.render("website_profile.rank_badge_main", values)

    def _prepare_all_users_values(self, users):
        return [
            {
                "id": user.id,
                "name": user.name,
                "company_name": user.company_id.name,
                "rank": user.rank_id.name,
                "karma": user.karma,
                "badge_count": len(user.badge_ids),
                "website_published": user.website_published,
            }
            for user in users
        ]

    @http.route(
        ["/profile/users", "/profile/users/page/<int:page>"],
        type="http",
        auth="public",
        website=True,
        sitemap=True,
        readonly=True,
        list_as_website_content=_lt("User Profiles"),
    )
    def view_all_users_page(self, page=1, **kwargs):
        User = request.env["res.users"]
        dom = [("karma", ">", 1), ("website_published", "=", True)]

        search_term = kwargs.get("search")
        group_by = kwargs.get("group_by", False)
        render_values = {
            "search": search_term,
            "group_by": group_by or "all",
        }
        if search_term:
            dom = Domain.AND(
                [
                    [
                        "|",
                        ("name", "ilike", search_term),
                        ("partner_id.commercial_company_name", "ilike", search_term),
                    ],
                    dom,
                ]
            )

        user_count = User.sudo().search_count(dom)
        my_user = request.env.user
        current_user_values = False
        if user_count:
            page_count = math.ceil(user_count / self._users_per_page)
            pager = request.website.pager(
                url="/profile/users",
                total=user_count,
                page=page,
                step=self._users_per_page,
                scope=min(self._pager_max_pages, page_count),
                url_args=kwargs,
            )

            users = User.sudo().search(
                dom,
                limit=self._users_per_page,
                offset=pager["offset"],
                order="karma DESC",
            )
            user_values = self._prepare_all_users_values(users)

            position_domain = [("karma", ">", 1), ("website_published", "=", True)]
            position_map = self._get_position_map(position_domain, users, group_by)

            max_position = max(
                [user_data["karma_position"] for user_data in position_map.values()],
                default=1,
            )
            for user in user_values:
                user_data = position_map.get(user["id"], {})
                user["position"] = user_data.get("karma_position", max_position + 1)
                user["karma_gain"] = user_data.get("karma_gain_total", 0)
            user_values.sort(key=itemgetter("position"))

            if (
                my_user.website_published
                and my_user.karma
                and my_user.id not in users.ids
            ):
                current_user = User.sudo().search(
                    Domain.AND([[("id", "=", my_user.id)], dom])
                )
                if current_user:
                    current_user_values = self._prepare_all_users_values(current_user)[
                        0
                    ]

                    user_data = self._get_position_map(
                        position_domain, current_user, group_by
                    ).get(current_user.id, {})
                    current_user_values["position"] = user_data.get("karma_position", 0)
                    current_user_values["karma_gain"] = user_data.get(
                        "karma_gain_total", 0
                    )

        else:
            user_values = []
            pager = {"page_count": 0}
        render_values.update(
            {
                "top3_users": user_values[:3] if not search_term and page == 1 else [],
                "users": user_values,
                "my_user": current_user_values,
                "pager": pager,
                **self._prepare_url_from_info(),
            }
        )
        return request.render("website_profile.users_page_main", render_values)

    def _get_position_map(self, position_domain, users, group_by):
        if group_by:
            position_map = self._get_user_tracking_karma_gain_position(
                position_domain, users.ids, group_by
            )
        else:
            position_results = users._get_karma_position(position_domain)
            position_map = {
                user_data["user_id"]: dict(user_data) for user_data in position_results
            }
        return position_map

    def _get_user_tracking_karma_gain_position(self, domain, user_ids, group_by):
        to_date = fields.Date.today()
        if group_by == "week":
            from_date = to_date - relativedelta(weeks=1)
        elif group_by == "month":
            from_date = to_date - relativedelta(months=1)
        else:
            from_date = None
        results = (
            request.env["res.users"]
            .browse(user_ids)
            ._get_tracking_karma_gain_position(
                domain, from_date=from_date, to_date=to_date
            )
        )
        return {item["user_id"]: dict(item) for item in results}

    @http.route(
        "/profile/send_validation_email", type="jsonrpc", auth="user", website=True
    )
    def send_validation_email(self, **kwargs):
        if request.env.uid != request.website.user_id.id:
            request.env.user._send_profile_validation_email(**kwargs)
        request.session["validation_email_sent"] = True
        return True

    @http.route(
        "/profile/validate_email",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def confirm_email(self, token, user_id, email, **kwargs):
        done = (
            request.env["res.users"]
            .sudo()
            .browse(int(user_id))
            ._process_profile_validation_token(token, email)
        )
        if done:
            request.session["validation_email_done"] = True
        url = kwargs.get("redirect_url", "/")
        return request.redirect(url)

    @http.route(
        "/profile/validate_email/close", type="jsonrpc", auth="public", website=True
    )
    def close_email_confirmation(self, **kwargs):
        request.session["validation_email_done"] = False
        request.session["validation_email_sent"] = False
        return True
