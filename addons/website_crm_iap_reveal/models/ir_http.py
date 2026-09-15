import logging
import time

from odoo import models
from odoo.http import request
from odoo.libs.debug_log import DebugLog

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _serve_page(cls):
        response = super()._serve_page()
        if (
            response
            and getattr(response, "status_code", 0) == 200
            and request.env.user._is_public()
        ):
            visitor_sudo = request.env["website.visitor"]._get_visitor_from_request()
            if not (visitor_sudo and visitor_sudo.lead_ids):
                country_code = request.geoip.country_code
                state_code = (
                    request.geoip.subdivisions[0].iso_code
                    if request.geoip.subdivisions
                    else None
                )
                if country_code:
                    try:
                        url = request.httprequest.url
                        ip_address = request.httprequest.remote_addr
                        if not ip_address:
                            return response
                        website_id = request.website.id
                        rules_excluded = (request.cookies.get("rule_ids") or "").split(
                            ","
                        )
                        before = time.time()
                        new_rules_excluded = (
                            request.env["crm.reveal.view"]
                            .sudo()
                            ._create_reveal_view(
                                website_id,
                                url,
                                ip_address,
                                country_code,
                                state_code,
                                rules_excluded,
                            )
                        )
                        _logger.info(
                            "Reveal process time: [%s], match rule: [%s?], country code: [%s], ip: [%s]",
                            time.time() - before,
                            new_rules_excluded == rules_excluded,
                            country_code,
                            ip_address,
                        )
                        if new_rules_excluded:
                            response.set_cookie(
                                "rule_ids",
                                ",".join(new_rules_excluded),
                                expires=None,
                                cookie_type="optional",
                            )
                    except Exception:
                        _logger.exception("Failed to process reveal rules")
                        _debug.logic("reveal_failed", website=website_id)
        return response
