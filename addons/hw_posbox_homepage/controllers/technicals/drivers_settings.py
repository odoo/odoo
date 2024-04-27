
from odoo import http
from odoo.addons.hw_drivers.tools import helpers
from odoo.addons.hw_posbox_homepage.controllers.table_info import TableInfo
from odoo.addons.hw_posbox_homepage.controllers.technical import get_technical_menu_by_module_name
from odoo.addons.hw_posbox_homepage.controllers.jinja import render_template


def get_six_terminal():
    terminal_id = helpers.read_file_first_line('odoo-six-payment-terminal.conf')
    return terminal_id or 'Not Configured'


class IoTTechnicalCredentialPage(http.Controller):
    @http.route('/technical/driver_settings', type='http', auth='none', website=True)
    def drivers_settings(self):
        drivers_table = []
        if helpers.IS_BOX:
            drivers_table.append(TableInfo('Printers', '', f"http://{helpers.get_ip()}:631", 'Printing Server', '_blank'))
        six_payment_terminal_menu = get_technical_menu_by_module_name('six_payment_terminal')
        if six_payment_terminal_menu.is_active:
            drivers_table.append(TableInfo('SIX Payment Terminal', get_six_terminal(), six_payment_terminal_menu.url))

        return render_template('technical/drivers_settings.jinja2', drivers_table=drivers_table)
