/* global owl */

const { Component, mount, xml, useState } = owl;

class StatusPage extends Component {
    static props = {};

    setup() {
        this.state = useState({ data: {}, loading: true });

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
            <p class="iotbox-name mt-3">IoT Box: <t t-out="state.data.hostname"/></p>
        </div>
        <div class="status-display-boxes">
            <div t-if="state.data.pairing_code" class="status-display-box">
                <h4 class="text-center mb-3">Pairing Code</h4>
                <hr/>
                <h4 t-out="state.data.pairing_code" class="text-center mb-3"/>
            </div>
            <div class="status-display-box">
                <h4 class="text-center mb-3">Status display</h4>
                <h5 class="text-center mb-1">IoT Interfaces</h5>
                <table class="table table-hover table-sm">
                    <thead>
                        <tr>
                            <th>Type</th>
                            <th>IP</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr t-foreach="state.data.network_interfaces" t-as="interface" t-key="interface.id">
                            <td><i t-att-class="'me-1 fa fa-fw fa-' + (interface.is_wifi ? 'wifi' : 'sitemap')"/><t t-out="interface.is_wifi ? interface.ssid : 'Ethernet'"/></td>
                            <td t-out="interface.ip"/>
                        </tr>
                    </tbody>
                </table>
                <div t-if="Object.keys(state.data.devices).length > 0">
                    <h5 class="text-center mb-1">IoT Devices</h5>
                    <table class="table table-hover table-sm">
                        <thead>
                            <tr>
                                <th>Type</th>
                                <th>Devices</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr t-foreach="Object.keys(state.data.devices)" t-as="deviceType" t-key="deviceType">
                                <td t-out="deviceType.replaceAll('_', ' ') + 's'" class="device-type"/>
                                <td>
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
