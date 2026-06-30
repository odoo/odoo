/* global owl */
import { DEVICE_ICONS } from "./components/dialog/DeviceDialog.js";

const { Component, mount, xml, useState } = owl;

const STATUS_POLL_DELAY_MS = 5000;

class StatusPage extends Component {
    static props = {};

    setup() {
        this.state = useState({ data: {}, loading: true });
        this.icons = DEVICE_ICONS;

        this.loadInitialData();
    }

    async loadInitialData() {
        try {
            const response = await fetch("/iot_drivers/data");
            this.state.data = await response.json();
            this.state.loading = false;
        } catch {
            console.warn("Error while fetching data");
        }
        setTimeout(() => this.loadInitialData(), STATUS_POLL_DELAY_MS);
    }

    get accessPointSsid() {
        return this.state.data.network_interfaces.filter((i) => i.is_wifi)[0]?.ssid;
    }

    static template = xml`
    <t t-translation="off">
        <div class="text-center pt-5">
            <img class="odoo-logo" src="/web/static/img/logo2.png" alt="Odoo logo"/>
        </div>
        <div t-if="state.loading || state.data.new_database_url" class="position-fixed top-0 start-0 vh-100 w-100 justify-content-center align-items-center d-flex flex-column gap-5">
            <div class="spinner-border">
                <span class="visually-hidden">Loading...</span>
            </div>
            <span t-if="state.data.new_database_url" class="fs-4">
                Connecting to <t t-out="state.data.new_database_url"/>, please wait
            </span>
        </div>
        <div t-else="" class="container-fluid">
            <!-- QR Codes shown on status page -->
            <div class="qr-code-box">
                <div class="status-display-box qr-code">
                    <div>
                        <h4 class="text-center mb-1">IoT Box Configuration</h4>
                        <hr/>
                        <!-- If the IoT Box is connected to internet -->
                        <div t-if="!state.data.is_access_point_up and state.data.qr_code_url">
                            <p>
                                1. Connect to
                                <!-- Only wifi connection is shown as ethernet connections look like "Wired connection 2" -->
                                <t t-if="state.data.wifi_ssid">
                                    <b>
                                        <t t-out="state.data.wifi_ssid"/>
                                    </b>
                                </t>
                                <t t-else=""> the IoT Box network</t>
                                <br/>
                                <br/>
                                <div t-if="state.data.qr_code_wifi" class="qr-code">
                                    <img t-att-src="state.data.qr_code_wifi" alt="QR Code Wi-FI"/>
                                </div>
                            </p>
                            <p>
                                2. Open the IoT Box setup page
                                <br/>
                                <br/>
                                <div class="qr-code">
                                    <img t-att-src="state.data.qr_code_url" alt="QR Code Homepage"/>
                                </div>
                            </p>
                        </div>
                        <!-- If the IoT Box is in access point and not connected to internet yet -->
                        <div t-elif="state.data.is_access_point_up and state.data.qr_code_wifi and state.data.qr_code_url"> 
                            <p>Scan this QR code with your smartphone to connect to the IoT box's <b>Wi-Fi hotspot</b>:</p>
                            <div class="qr-code">
                                <img t-att-src="state.data.qr_code_wifi" alt="QR Code Access Point"/>
                            </div>
                            <br/>
                            <br/>
                            <p>Once you are connected to the Wi-Fi hotspot, you can scan this QR code to access the IoT box <b>Wi-Fi configuration page</b>:</p>
                            <div class="qr-code">
                                <img t-att-src="state.data.qr_code_url" alt="QR Code Wifi Config"/>
                            </div>
                            <br/>
                            <br/>
                        </div>
                    </div>
                </div>
            </div>
            <div class="status-display-boxes">
                <div t-if="(state.data.pairing_code || state.data.pairing_code_expired) and !state.data.is_access_point_up" class="status-display-box">
                    <h4 class="text-center mb-3">Pairing Code</h4>
                    <hr/>
                    <t t-if="state.data.pairing_code and !state.data.pairing_code_expired">
                        <h4 t-out="state.data.pairing_code" class="text-center mb-3"/>
                        <p class="text-center mb-3">
                            Enter this code in the IoT app in your Odoo database to pair the IoT Box.
                        </p>
                    </t>
                    <p t-else="" class="text-center mb-3">
                        The pairing code has expired. Please restart your IoT Box to generate a new one.
                    </p>
                </div>
                <div t-if="state.data.is_access_point_up and accessPointSsid" class="status-display-box">
                    <h4 class="text-center mb-3">No Internet Connection</h4>
                    <hr/>
                    <p class="mb-3">
                        Please connect your IoT Box to internet via an ethernet cable or connect to Wi-FI network<br/>
                        <a class="alert-link" t-out="accessPointSsid" /><br/>
                        to configure a Wi-Fi connection on the IoT Box
                    </p>
                </div>
                <div class="status-display-box">
                    <h4 class="text-center mb-3">Status display</h4>
                    
                    <h5 class="mb-1">General</h5>
                    <table class="table table-hover table-sm">
                        <tbody>
                            <tr>
                                <td class="col-3"><i class="me-1 fa fa-fw fa-id-card"/>Identifier</td>
                                <td class="col-3" t-out="state.data.identifier"/>
                            </tr>
                            <tr>
                                <td class="col-3"><i class="me-1 fa fa-fw fa-address-book"/>Mac Address</td>
                                <td class="col-3" t-out="state.data.mac_address"/>
                            </tr>
                            <tr t-if="state.data.server_status">
                                <td class="col-3"><i class="me-1 fa fa-fw fa-database"/>Database</td>
                                <td class="col-3" t-out="state.data.server_status"/>
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
                                        <t t-out="deviceType.replaceAll('_', ' ') + (deviceType === 'unsupported' ? '' : 's')"/>
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
    </t>
    `;
}

mount(StatusPage, document.body);
