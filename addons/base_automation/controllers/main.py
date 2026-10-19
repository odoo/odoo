from odoo.http import request, route, Controller
from odoo.addons.base_automation.models.base_automation import get_webhook_request_payload

class BaseAutomationController(Controller):

    @route(['/web/hook/<string:rule_uuid>'], type='http', auth='public', methods=['GET', 'POST'], csrf=False, save_session=False)
    def call_webhook_http(self, rule_uuid, **kwargs):
        """ Execute an automation webhook """
        rule = request.env['base.automation'].sudo().search([('webhook_uuid', '=', rule_uuid)])
        if not rule:
            return request.make_json_response({'status': 'error'}, status=404)

        data = get_webhook_request_payload()
        try:
            rule._execute_webhook(data)
        except Exception: # noqa: BLE001
            return request.make_json_response({'status': 'error'}, status=500)
        return request.make_json_response({'status': 'ok'}, status=200)
