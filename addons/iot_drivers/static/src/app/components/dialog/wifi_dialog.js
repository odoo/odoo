/* global owl */

import useStore from "../../hooks/store_hook.js";
import { Dialog } from "./dialog.js";
import { LoadingFullScreen } from "../loading_full_screen.js";

const { Component, xml, signal } = owl;

export class WifiDialog extends Component {
    static components = { Dialog, LoadingFullScreen };

    store = useStore();

    scanning = signal(true);
    waitRestart = signal(false);
    status = signal("");
    availableWiFi = signal([]);
    isPasswordVisible = signal(false);

    form = {
        essid: signal(""),
        password: signal(""),
    };

    onClose() {
        this.availableWiFi.set([]);
        this.scanning.set(true);
        this.form.essid.set("");
        this.form.password.set("");
    }

    isCurrentlyConnectedToWifi() {
        return (
            !this.store.base().is_access_point_up &&
            this.store.base().network_interfaces.some((netInterface) => netInterface.is_wifi)
        );
    }

    isCurrentlyConnectedToEthernet() {
        return this.store.base().network_interfaces.some((netInterface) => !netInterface.is_wifi);
    }

    async getWiFiNetworks() {
        try {
            const data = await this.store.rpc({
                url: "/iot_drivers/wifi",
            });
            this.form.essid.set(data.currentWiFi || "Select Network...");
            this.availableWiFi.set(data.availableWiFi);

            this.scanning.set(false);
        } catch {
            console.warn("Error while fetching data");
        }
    }

    async connectToWiFi() {
        if (!this.form.essid() || !this.form.password()) {
            return;
        }

        this.waitRestart.set(true);
        const responsePromise = this.store.rpc({
            url: "/iot_drivers/update_wifi",
            method: "POST",
            params: {
                essid: this.form.essid(),
                password: this.form.password(),
            },
        });
        if (this.isCurrentlyConnectedToEthernet()) {
            const data = await responsePromise;
            if (data.status !== "success") {
                this.waitRestart.set(false);
            }
        } else {
            // The IoT box is no longer reachable, so we can't await the response.
            this.status.set("connecting");
            this.waitRestart.set(false);
        }
    }

    async clearConfiguration() {
        try {
            this.waitRestart.set(true);
            const responsePromise = this.store.rpc({
                url: "/iot_drivers/wifi_clear",
            });
            if (this.isCurrentlyConnectedToEthernet()) {
                const data = await responsePromise;
                if (data.status !== "success") {
                    this.waitRestart.set(false);
                }
            } else {
                // The IoT box is no longer reachable, so we can't await the response.
                this.status.set("disconnecting");
                this.waitRestart.set(false);
            }
        } catch {
            console.warn("Error while clearing configuration");
        }
    }

    togglePasswordVisibility() {
        this.isPasswordVisible.set(!this.isPasswordVisible());
    }

    static template = xml`
    <t t-translation="off">
        <LoadingFullScreen t-if="this.waitRestart()">
            <t t-set-slot="body">
                Updating Wi-Fi configuration, please wait...
            </t>
        </LoadingFullScreen>

        <div t-if="this.status()" class="position-fixed top-0 start-0 bg-white vh-100 w-100 justify-content-center align-items-center d-flex always-on-top">
            <div class="alert alert-success mx-4">
                <t t-if="this.status() === 'connecting'">
                    The IoT Box will now attempt to connect to <t t-out="this.form.essid()"/>. The next step is to find your <b>pairing code</b>:
                    <ul>
                        <li>You will need a screen or a compatible USB printer connected.</li>
                        <li>In a few seconds, the pairing code should display on your screen and/or print from your printer.</li>
                        <li>Once you have the pairing code, you can enter it on the IoT app in your database to pair your IoT Box.</li>
                    </ul>
                    In the event that the pairing code does not appear, it may be because the IoT Box failed to connect to the Wi-Fi network.
                    In this case you will need to reconnect to the Wi-Fi hotspot and try again.
                </t>
                <t t-if="this.status() === 'disconnecting'">
                    The IoT Box Wi-Fi configuration has been cleared. You will need to connect to the IoT Box hotspot or connect an ethernet cable.
                </t>
            </div>
        </div>

        <Dialog
            name="'Configure Wi-Fi'"
            help="'https://www.odoo.com/documentation/latest/applications/general/iot/iot_box.html#iot-iot-box-network-wifi'"
            btnName="'Configure'"
            onOpen.bind="this.getWiFiNetworks"
            onClose.bind="this.onClose">
            <t t-set-slot="body">
                <div t-if="this.scanning()" class="position-absolute top-0 start-0 bg-white h-100 w-100 justify-content-center align-items-center d-flex flex-column gap-3 always-on-top">
                    <div class="spinner-border" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p>Currently scanning for available networks...</p>
                </div>

                <div class="alert alert-warning fs-6" role="alert">
                    Here, you can configure how the IoT Box should connect to wireless networks.
                    Currently, only Open and WPA networks are supported.
                </div>
                <div class="mt-3">
                    <div class="mb-3">
                        <select name="essid" class="form-control" id="wifi-ssid" t-model="this.form.essid">
                            <option>Select Network...</option>
                            <option t-foreach="this.availableWiFi().filter((wifi) => wifi)" t-as="wifi" t-key="wifi" t-att-value="wifi">
                                <t t-out="wifi"/>
                            </option>
                        </select>
                    </div>

                    <div class="mb-3 d-flex gap-1">
                        <input name="password" t-att-type="this.isPasswordVisible() ? '' : 'password'" class="form-control" aria-label="Username" aria-describedby="basic-addon1" t-model="this.form.password" placeholder="Wi-Fi password"/>
                        <button class="btn btn-secondary" type="button" t-on-click="this.togglePasswordVisibility">
                            <i t-att-class="'fa fa-eye' + (this.isPasswordVisible() ? '-slash' : '')"></i>
                        </button>
                    </div>
                </div>
            </t>
            <t t-set-slot="footer">
                <button type="submit" class="btn btn-primary btn-sm" t-att-disabled="this.form.essid() === 'Select Network...'" t-on-click="this.connectToWiFi">Connect</button>
                <button t-if="this.isCurrentlyConnectedToWifi()" type="submit" class="btn btn-secondary btn-sm" t-on-click="this.clearConfiguration">
                    Disconnect From Current
                </button>
                <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Close</button>
            </t>
        </Dialog>
    </t>
    `;
}
