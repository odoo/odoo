# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import Controller, request, route


class BusController(Controller):
    @route("/bus/has_missed_notifications", type="jsonrpc", auth="public")
    def has_missed_notifications(self, last_notification_id):
        # sudo - bus.bus: checking if a notification still exists in order to
        # detect missed notification during disconnect is allowed.
        return request.env["bus.bus"].sudo().search_count([("id", "=", last_notification_id)]) == 0
