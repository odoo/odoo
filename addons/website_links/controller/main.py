from odoo import http
from odoo.http import request
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class WebsiteUrl(http.Controller):
    @http.route("/website_links/new", type="jsonrpc", auth="user", methods=["POST"])
    def create_shorten_url(self, **post):
        if "url" not in post or post["url"] == "":
            _debug.logic("shorten_url_refused", reason="empty_url")
            return {"error": "empty_url"}
        _debug.lifecycle("shorten_url", campaign=post.get("campaign_id"))
        return (
            request.env["link.tracker"]
            .with_context(link_tracker_fetch_title=True)
            .search_or_create([post])
            .read()
        )

    @http.route("/r", type="http", auth="user", website=True)
    def shorten_url(self, **post):
        return request.render(
            "website_links.page_shorten_url",
            {
                "can_create_link_tracker": request.env["link.tracker"].has_access(
                    "create"
                ),
                "can_create_link_tracker_code": request.env[
                    "link.tracker.code"
                ].has_access("create"),
                **post,
            },
        )

    @http.route("/website_links/add_code", type="jsonrpc", auth="user")
    def add_code(self, **post):
        link_id = (
            request.env["link.tracker.code"]
            .search([("code", "=", post["init_code"])], limit=1)
            .link_id.id
        )
        existing = request.env["link.tracker.code"].search(
            [("code", "=", post["new_code"]), ("link_id", "=", link_id)], limit=1
        )
        if existing:
            _debug.logic("link_code_reused", link=link_id, code=post.get("new_code"))
            return existing.read()
        _debug.lifecycle("link_code_created", link=link_id, code=post.get("new_code"))
        return (
            request.env["link.tracker.code"]
            .create({"code": post["new_code"], "link_id": link_id})
            .read()
        )

    @http.route("/website_links/recent_links", type="jsonrpc", auth="user")
    def recent_links(self, **post):
        return request.env["link.tracker"].recent_links(post["filter"], post["limit"])

    @http.route("/r/<string:code>+", type="http", auth="user", website=True)
    def statistics_shorten_url(self, code, **post):
        code = request.env["link.tracker.code"].search([("code", "=", code)], limit=1)

        if code:
            return request.render(
                "website_links.graphs",
                {
                    "can_create_link_tracker_code": request.env[
                        "link.tracker.code"
                    ].has_access("create"),
                    **code.link_id.read()[0],
                },
            )
        else:
            _debug.logic("link_statistics_unknown_code")
            return request.redirect("/", code=301)
