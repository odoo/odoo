from odoo.http import Controller, request, route

from odoo.addons.automation_webhook.models.automation_rule import (
    get_webhook_request_payload,
)


class AutomationRuleController(Controller):
    # csrf=False: auth="receiver" admits the caller through its inbound gate
    @route(
        ["/web/hook/<string:webhook_uuid>"],
        type="http",
        auth="receiver",
        receiver="automation.rule:_receiver_for_webhook",
        receiver_event="webhook",
        methods=["GET", "POST"],
        csrf=False,
        save_session=False,
        typed=True,
    )
    def call_webhook_http(self, webhook_uuid: str, **kwargs):
        admission = request.admission
        rule = admission.subject
        data = get_webhook_request_payload()
        try:
            rule._execute_webhook(data, admission)
        except Exception:
            return request.prepare_json_response({"status": "error"}, status=500)
        return request.prepare_json_response({"status": "ok"}, status=200)
