from urllib.parse import unquote, urlsplit
from werkzeug.exceptions import NotFound

from odoo.http import request

from odoo.addons.mail.controllers.discuss import public_page
from odoo.addons.mail.tools.discuss import Store, mail_route


class PublicPageController(public_page.PublicPageController):
    def _portal_discuss_navigation_values(self):
        """Return navigation data only for authenticated portal users.

        A referrer is used only when it points to a regular portal page on the
        same origin. This avoids exposing the action to guests and prevents an
        arbitrary return URL from turning the link into an open redirect.
        """
        user = request.env.user
        if not user._is_portal() or user._is_internal():
            return {}

        navigation_url = "/my/home"
        has_origin = False
        referrer = request.httprequest.referrer
        if referrer:
            try:
                parsed_referrer = urlsplit(referrer)
                parsed_root = urlsplit(request.httprequest.url_root)
                path = unquote(parsed_referrer.path)
                is_same_origin = (
                    parsed_referrer.scheme == parsed_root.scheme
                    and parsed_referrer.netloc == parsed_root.netloc
                )
                is_portal_path = path == "/my" or path.startswith("/my/")
                is_discuss_path = path == "/my/conversations" or path.startswith(
                    "/my/conversations/"
                )
                has_unsafe_segment = "\\" in path or any(
                    segment in (".", "..") for segment in path.split("/")
                )
                if is_same_origin and is_portal_path and not is_discuss_path and not has_unsafe_segment:
                    navigation_url = parsed_referrer.path
                    if parsed_referrer.query:
                        navigation_url += f"?{parsed_referrer.query}"
                    has_origin = True
            except ValueError:
                # Ignore malformed referrers and keep the safe portal-home fallback.
                pass
        return {
            "portalDiscussHasOrigin": has_origin,
            "portalDiscussNavigationUrl": navigation_url,
        }

    def _response_discuss_public_template(self, store, channel=None):
        navigation_values = self._portal_discuss_navigation_values()
        if navigation_values:
            store.add_global_values(**navigation_values)
        return super()._response_discuss_public_template(store, channel)

    @mail_route("/my/conversations", methods=["GET"], type="http", auth="user")
    def discuss_portal(self):
        return self._response_discuss_public_template(Store())

    @mail_route("/my/conversations/<int:channel_id>", methods=["GET"], type="http", auth="user")
    def discuss_portal_channel(self, channel_id):
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel:
            raise NotFound()
        return self._response_discuss_public_template(Store(), channel)
