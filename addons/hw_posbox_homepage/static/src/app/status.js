/* global owl */
import { DEVICE_ICONS } from "./components/dialog/DeviceDialog.js";

const { Component, mount, xml, useState } = owl;

class StatusPage extends Component {
    static props = {};

    setup() {
        this.state = useState({ data: {}, loading: true });
        this.icons = DEVICE_ICONS;

        this.loadInitialData();
        setInterval(() => {
            this.loadInitialData();
        }, 10000);
    }

    async loadInitialData() {
        try {
            const response = await fetch("/hw_posbox_homepage/data");
            this.state.data = await response.json();
            this.state.loading = false;
        } catch {
            console.warn("Error while fetching data");
        }
    }

    static template = xml`
    <div t-if="!state.loading" class="container-fluid">
        <div class="text-center pt-5">
            <img class="odoo-logo" src="/web/static/img/logo2.png" alt="Odoo logo"/>
        </div>
        <div class="status-display-boxes">
            <div t-if="state.data.pairing_code" class="status-display-box">
                <h4 class="text-center mb-3">Pairing Code</h4>
                <hr/>
                <h4 t-out="state.data.pairing_code" class="text-center mb-3"/>
            </div>
            <div t-if="state.data.is_access_point_up" class="status-display-box">
                <h4 class="text-center mb-3">No Internet Connection</h4>
                <hr/>
                <p class="mb-3">
                    Please connect your IoT Box to internet via an ethernet cable or connect to Wi-FI network<br/>
                    <a class="alert-link" t-out="'IoTBox-' + (state.data.network_interfaces[0].ssid or state.data.mac.replace(':', ''))" /><br/>
                    to configure a Wi-Fi connection on the IoT Box
                </p>
            </div>
            <div class="status-display-box">
                <h4 class="text-center mb-3">Status display</h4>
                
                <h5 class="mb-1">General</h5>
                <table class="table table-hover table-sm">
                    <tbody>
                        <tr>
                            <td class="col-3"><i class="me-1 fa fa-fw fa-id-card"/>Name</td>
                            <td class="col-3" t-out="state.data.hostname"/>
                        </tr>
                    </tbody>
                </table>
                
                <h5 class="mb-1" t-if="state.data.network_interfaces.length > 0">Internet Connection</h5>
                <table class="table table-hover table-sm" t-if="state.data.network_interfaces.length > 0">
                    <tbody>
                        <tr t-foreach="state.data.network_interfaces" t-as="interface" t-key="interface.id">
                            <td class="col-3"><i t-att-class="'me-1 fa fa-fw fa-' + (interface.is_wifi ? 'wifi' : 'sitemap')"/><t t-out="interface.is_wifi ? interface.ssid : 'Ethernet'"/></td>
                            <td class="col-3" t-out="interface.ip"/>
                        </tr>
                    </tbody>
                </table>
                <div t-if="Object.keys(state.data.devices).length > 0">
                    <h5 class="mb-1">Devices</h5>
                    <table class="table table-hover table-sm">
                        <tbody>
                            <tr t-foreach="Object.keys(state.data.devices)" t-as="deviceType" t-key="deviceType">
                                <td class="device-type col-3">
                                    <i t-att-class="'me-1 fa fa-fw fa- ' + icons[deviceType]"/>
                                    <t t-out="deviceType.replaceAll('_', ' ') + 's'" />
                                </td>
                                <td class="col-3">
                                    <ul>
                                        <li t-foreach="state.data.devices[deviceType].slice(0, 10)" t-as="device" t-key="device.identifier">
                                            <t t-out="device.name"/>
                                        </li>
                                        <li t-if="state.data.devices[deviceType].length > 10">...</li>
                                    </ul>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    `;
}

mount(StatusPage, document.body);
