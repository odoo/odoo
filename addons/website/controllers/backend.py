import werkzeug

from odoo import http
from odoo.http import request
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class WebsiteBackend(http.Controller):
    @http.route(
        "/website/fetch_dashboard_data", type="jsonrpc", auth="user", readonly=True
    )
    def get_dashboard_data(self, website_id):
        Website = request.env["website"]
        has_group_system = request.env.user.has_group("base.group_system")
        has_group_designer = request.env.user.has_group(
            "website.group_website_designer"
        )
        dashboard_data = {
            "groups": {
                "system": has_group_system,
                "website_designer": has_group_designer,
            },
            "dashboards": {},
        }

        current_website = (
            website_id and Website.browse(website_id).exists()
        ) or Website.get_current_website()
        multi_website = request.env.user.has_group("website.group_multi_website")
        websites = (
            multi_website and request.env["website"].search([])
        ) or current_website
        dashboard_data["websites"] = websites.read(["id", "name"])
        for website in dashboard_data["websites"]:
            if website["id"] == current_website.id:
                website["selected"] = True

        if has_group_designer:
            dashboard_data["dashboards"]["plausible_share_url"] = (
                current_website._get_plausible_share_url()
            )
        _debug.pipeline(
            "dashboard_data",
            website=current_website.id,
            websites=len(dashboard_data["websites"]),
            designer=has_group_designer,
            system=has_group_system,
        )
        return dashboard_data

    @http.route(
        "/website/iframefallback", type="http", auth="user", website=True, readonly=True
    )
    def get_iframe_fallback(self):
        return request.render("website.iframefallback")

    @http.route(
        "/website/check_new_content_access_rights",
        type="jsonrpc",
        auth="user",
        readonly=True,
    )
    def check_create_access_rights(self, models):
        if not request.env.user.has_group("website.group_website_restricted_editor"):
            _debug.logic("new_content_rights_refused", reason="not_restricted_editor")
            raise werkzeug.exceptions.Forbidden

        return {model: request.env[model].has_access("create") for model in models}

    @http.route(
        "/website/track_installing_modules", type="jsonrpc", auth="user", readonly=True
    )
    def website_track_installing_modules(self, selected_features, total_features=None):
        features_not_installed = (
            request.env["website.configurator.feature"]
            .browse(selected_features)
            .module_id.upstream_dependencies(exclude_states=("",))
            .filtered(lambda feature: feature.state != "installed")
        )

        total_features = total_features or len(features_not_installed)
        _debug.pipeline(
            "module_install_progress",
            total=total_features,
            remaining=len(features_not_installed),
        )
        return {
            "total": total_features,
            "nbInstalled": total_features - len(features_not_installed),
        }
