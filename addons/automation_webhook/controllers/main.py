from odoo.http import Controller, request, route

from odoo.addons.automation_webhook.models.automation_rule import (
    get_webhook_request_payload,
)


class AutomationRuleController(Controller):
    @route(
        ["/web/hook/<string:rule_uuid>"],
        type="http",
        auth="public",
        methods=["GET", "POST"],
        csrf=False,
        save_session=False,
    )
    def call_webhook_http(self, rule_uuid, **kwargs):
        rule = (
            request.env["automation.rule"]
            .sudo()
            .search(
                [
                    ("webhook_uuid", "=", rule_uuid),
                    ("trigger", "=", "on_webhook"),
                ],
                limit=1,
            )
        )
        if not rule:
            request.env["inbound.access.log"]._record_unknown_caller(
                "automation.rule",
                f"uuid {rule_uuid[:8]}",
                request.httprequest.remote_addr,
                user_agent=request.httprequest.headers.get("User-Agent"),
            )
            return request.prepare_json_response({"status": "error"}, status=404)

        ok, status, message = rule._check_webhook_request(
            headers=dict(request.httprequest.headers),
            body=request.httprequest.get_data(as_text=False),
            remote_addr=request.httprequest.remote_addr,
        )
        if not ok:
            return request.prepare_json_response(
                {"status": "error", "message": message}, status=status
            )

        data = get_webhook_request_payload()
        try:
            rule._execute_webhook(data)
        except Exception:
            return request.prepare_json_response({"status": "error"}, status=500)
        return request.prepare_json_response({"status": "ok"}, status=200)
