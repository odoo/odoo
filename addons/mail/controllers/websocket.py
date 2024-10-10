from odoo.addons.bus.controllers.websocket import WebsocketController
from odoo.http import request, route, SessionExpiredException


class WebsocketControllerPresence(WebsocketController):
    @route('/websocket/update_bus_presence', type='json', auth='public', cors='*')
    def update_bus_presence(self, inactivity_period, im_status_ids_by_model):
        if 'is_websocket_session' not in request.session:
            raise SessionExpiredException()
        request.env['ir.websocket']._update_bus_presence(int(inactivity_period), im_status_ids_by_model)
        return {}

    def get_subscribe_data(self, channels, last):
        subscribe_data = super().get_subscribe_data(channels, last)
        if bus_target := request.env["ir.websocket"]._get_missed_presences_bus_target():
            subscribe_data["missed_presences"]._send_presence(bus_target=bus_target)
        return subscribe_data
