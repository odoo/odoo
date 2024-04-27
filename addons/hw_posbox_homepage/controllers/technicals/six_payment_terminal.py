import logging


from odoo import http, service
from odoo.addons.hw_drivers.tools import helpers
from odoo.addons.hw_posbox_homepage.controllers.technical import IoTTechnicalPage, get_menu
from odoo.addons.hw_posbox_homepage.controllers.technicals.drivers_settings import get_six_terminal

_logger = logging.getLogger(__name__)


class IoTBoxTechnicalCredentialPage(http.Controller, IoTTechnicalPage):
    _menu = get_menu(__name__)

    @http.route(_menu.url, type='http', auth='none', cors='*', csrf=False)
    def six_payment_terminal(self):
        return self.render(
            title='Six Payment Terminal',
            terminalId=get_six_terminal(),
        )

    @http.route('/six_payment_terminal_add', type='http', auth='none', cors='*', csrf=False)
    def add_six_payment_terminal(self, terminal_id):
        if terminal_id.isdigit():
            helpers.write_file('odoo-six-payment-terminal.conf', terminal_id)
            service.server.restart()
        else:
            _logger.warning('Ignoring invalid Six TID: "%s". Only digits are allowed', terminal_id)
            self.clear_six_payment_terminal()
        return 'http://' + helpers.get_ip() + ':8069'

    @http.route('/six_payment_terminal_clear', type='http', auth='none', cors='*', csrf=False)
    def clear_six_payment_terminal(self):
        helpers.unlink_file('odoo-six-payment-terminal.conf')
        service.server.restart()
        return "<meta http-equiv='refresh' content='0; url=http://" + helpers.get_ip() + ":8069'>"
