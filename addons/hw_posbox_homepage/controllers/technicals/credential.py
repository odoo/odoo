
from odoo import http
from odoo.addons.hw_drivers.tools import helpers
from odoo.addons.hw_posbox_homepage.controllers.technical import IoTTechnicalPage, get_menu


class IoTBoxTechnicalCredentialPage(http.Controller, IoTTechnicalPage):
    _menu = get_menu(__name__)

    @http.route(_menu.url, type='http', auth='none', website=True)
    def list_credential(self):
        return self.render(
            db_uuid=helpers.read_file_first_line('odoo-db-uuid.conf'),
            enterprise_code=helpers.read_file_first_line('odoo-enterprise-code.conf'),
        )

    @http.route('/save_credential', type='http', auth='none', cors='*', csrf=False)
    def save_credential(self, db_uuid, enterprise_code):
        helpers.write_file('odoo-db-uuid.conf', db_uuid)
        helpers.write_file('odoo-enterprise-code.conf', enterprise_code)
        helpers.odoo_restart(0)
        return "<meta http-equiv='refresh' content='20; url=http://" + helpers.get_ip() + ":8069'>"

    @http.route('/clear_credential', type='http', auth='none', cors='*', csrf=False)
    def clear_credential(self):
        helpers.unlink_file('odoo-db-uuid.conf')
        helpers.unlink_file('odoo-enterprise-code.conf')
        helpers.odoo_restart(0)
        return "<meta http-equiv='refresh' content='20; url=http://" + helpers.get_ip() + ":8069'>"
