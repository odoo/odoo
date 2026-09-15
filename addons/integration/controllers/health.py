import logging

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request

from odoo.addons.integration.tools.exceptions import CommError

_logger = logging.getLogger(__name__)


class IntegrationHealthController(http.Controller):
    @http.route(
        "/api_transport/health",
        type="jsonrpc",
        auth="user",
        methods=["POST"],
    )
    def health_check(self, endpoint_code):
        if not request.env.user.has_group("integration.group_api_transport_user"):
            _logger.warning(
                "Unauthorized /api_transport/health probe by user %s for %s",
                request.env.user.login,
                endpoint_code,
            )
            return {"status": "error", "error": "forbidden"}

        try:
            service = (
                request.env["integration.service"]
                .sudo()
                .search([("code", "=", endpoint_code), ("active", "=", True)], limit=1)
            )
            if not service:
                return {"status": "error", "error": "unknown_service"}
            client = service._get_api_client()
            is_healthy = client.probe_health()
        except (CommError, UserError) as e:
            _logger.warning("Health check failed for service %s: %s", endpoint_code, e)
            return {
                "status": "error",
                "service": endpoint_code,
                "error": "unavailable",
            }
        except Exception:
            _logger.exception(
                "Unexpected error on /api_transport/health for service %s",
                endpoint_code,
            )
            return {
                "status": "error",
                "service": endpoint_code,
                "error": "internal_error",
            }

        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "service": endpoint_code,
        }
