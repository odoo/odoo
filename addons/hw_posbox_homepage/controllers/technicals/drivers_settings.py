
from odoo import http
from odoo.addons.hw_drivers.tools import helpers
from odoo.addons.hw_posbox_homepage.controllers.table_info import TableInfo
from odoo.addons.hw_posbox_homepage.controllers.technical import IS_LINUX, IoTTechnicalPage, get_menu



def get_six_terminal():
    terminal_id = helpers.read_file_first_line('odoo-six-payment-terminal.conf')
    return terminal_id or 'Not Configured'


class IoTBoxTechnicalCredentialPage(http.Controller, IoTTechnicalPage):
    _menu = get_menu(__name__)

    @http.route(_menu.url, type='http', auth='none', website=True)
    def drivers_settings(self):
        drivers_table = []
        if IS_LINUX:
            drivers_table.append(TableInfo('Printers', '', f"http://{helpers.get_ip()}:631", 'Printing Server', '_blank'))
        six_sub_menu = self._menu.get_submenu('SIX Payment Terminal')
        if six_sub_menu:
            drivers_table.append(TableInfo(six_sub_menu.name, get_six_terminal(), six_sub_menu.url))

        return self.render(drivers_table=drivers_table)
