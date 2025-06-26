# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.http import Controller, request, route


class BusController(Controller):
    @route('/bus/get_model_definitions', methods=['POST'], type='http', auth='user')
    def get_model_definitions(self, model_names_to_fetch, **kwargs):
        return request.make_response(json.dumps(
            request.env['ir.model']._get_model_definitions(json.loads(model_names_to_fetch)),
        ))

    @route("/bus/has_missed_notifications", type="json", auth="public")
    def has_missed_notifications(self, last_notification_id):
        # sudo - bus.bus: checking if a notification still exists in order to
        # detect missed notification during disconnect is allowed.
        return request.env["bus.bus"].sudo().search_count([("id", "=", last_notification_id)]) == 0

    @route("/bus/get_autovacuum_info", type="json", auth="public")
    def get_autovacuum_info(self):
        # sudo - ir.cron: lastcall and nextcall of the autovacuum is not sensitive
        return request.env.ref("base.autovacuum_job").sudo().read(["lastcall", "nextcall"])[0]
