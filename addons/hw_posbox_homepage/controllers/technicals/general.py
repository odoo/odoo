
from odoo import http
from odoo.addons.hw_drivers.tools import helpers
from odoo.addons.hw_posbox_homepage.controllers.table_info import TableInfo
from odoo.addons.hw_posbox_homepage.controllers.technical import get_technical_menu_by_module_name
from odoo.addons.hw_posbox_homepage.controllers.jinja import render_template


class IoTTechnicalGeneralPage(http.Controller):
    @http.route('/technical', type='http', auth='none')
    def technical_route(self):
        network_type = 'Not Connected'
        is_ethernet = True
        ssid = None
        if helpers.IS_BOX:
            is_ethernet = helpers.read_file_first_line('/sys/class/net/eth0/operstate') == 'up'
            ssid = helpers.get_ssid()
        if is_ethernet:
            network_type = 'Ethernet'
        elif ssid:
            network_type = 'Wifi access point' if helpers.access_point() else 'Wifi: ' + ssid

        is_certificate_ok, certificate_details = helpers.get_certificate_status()

        update_menu = get_technical_menu_by_module_name('update')
        network_type_menu = get_technical_menu_by_module_name('wifi')

        infos_table = (
            TableInfo('Version', helpers.get_version(), update_menu.is_active and update_menu.url, 'update', iot_documentation_url='/config/updating_iot.html'),
            TableInfo('IP Address', helpers.get_ip()),
            TableInfo('MAC Address', helpers.get_mac_address()),
            TableInfo('Network Type', network_type, network_type_menu.is_active and network_type_menu.url),
            TableInfo(
                'HTTPS Certificate',
                f"""<details>
                <summary>OK</summary>
                <code>{ certificate_details }</code>
                </details>""" if is_certificate_ok else
                f"""ERROR, can't load certificate:<br/>
                <small><code>{certificate_details}</small></code>""",
                iot_documentation_url='/config/https_certificate_iot.html',
                action_iot_documentation_url=not is_certificate_ok and f'/config/https_certificate_iot.html#{certificate_details.replace("_", "-").lower()}',
                action_name='more details', action_target='_blank',
                is_warning=not is_certificate_ok
            )
        )
        return render_template('technical/general.jinja2', infos_table=infos_table)
