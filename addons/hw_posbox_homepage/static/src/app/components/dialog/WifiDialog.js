/* global owl */

import useStore from "../../hooks/useStore.js";
import { BootstrapDialog } from "./BootstrapDialog.js";
import { LoadingFullScreen } from "../LoadingFullScreen.js";

const { Component, xml, useState } = owl;

export class WifiDialog extends Component {
    static props = {};
    static components = { BootstrapDialog, LoadingFullScreen };

    setup() {
        this.store = useStore();
        this.state = useState({
            scanning: true,
            waitRestart: false,
            statusMessage: "",
            availableWiFi: [],
        });
        this.form = useState({
            essid: "",
            password: "",
        });
    }

    onClose() {
        this.state.availableWiFi = [];
        this.state.scanning = true;
        this.form.essid = "";
        this.form.password = "";
    }

    isCurrentlyConnectedToWifi() {
        return (
            !this.store.base.is_access_point_up &&
            this.store.base.network_interfaces.some((netInterface) => netInterface.is_wifi)
        );
    }

    isCurrentlyConnectedToEthernet() {
        return this.store.base.network_interfaces.some((netInterface) => !netInterface.is_wifi);
    }

    async getWiFiNetworks() {
        try {
            const data = await this.store.rpc({
                url: "/hw_posbox_homepage/wifi",
            });
            this.form.essid = data.currentWiFi;
            this.state.availableWiFi = data.availableWiFi;

            this.state.scanning = false;
        } catch {
            console.warn("Error while fetching data");
        }
    }

    async connectToWiFi() {
        if (!this.form.essid || !this.form.password) {
            return;
        }

        this.state.waitRestart = true;
        const responsePromise = this.store.rpc({
            url: "/hw_posbox_homepage/update_wifi",
            method: "POST",
            params: this.form,
        });
        if (this.isCurrentlyConnectedToEthernet()) {
            const data = await responsePromise;
            if (data.status !== "success") {
                this.state.waitRestart = false;
            }
        } else {
            // The IoT box is no longer reachable, so we can't await the response.
            this.state.statusMessage = `The IoT Box will now attempt to connect to ${this.form.essid}. You may close this page.`;
            this.state.waitRestart = false;
        }
    }

    async clearConfiguration() {
        try {
            this.state.waitRestart = true;
            const responsePromise = this.store.rpc({
                url: "/hw_posbox_homepage/wifi_clear",
            });
            if (this.isCurrentlyConnectedToEthernet()) {
                const data = await responsePromise;
                if (data.status !== "success") {
                    this.state.waitRestart = false;
                }
            } else {
                // The IoT box is no longer reachable, so we can't await the response.
                this.state.statusMessage = `The IoT Box Wi-Fi configuration has been cleared. You will need to connect to the IoT Box hotspot or connect an ethernet cable.`;
                this.state.waitRestart = false;
            }
        } catch {
            console.warn("Error while clearing configuration");
        }
    }

    static template = xml`
        <LoadingFullScreen t-if="this.state.waitRestart">
            <t t-set-slot="body">
                Processing your request please wait...
            </t>
        </LoadingFullScreen>

        <div t-if="state.statusMessage" class="position-fixed top-0 start-0 bg-white vh-100 w-100 justify-content-center align-items-center d-flex always-on-top">
            <div class="alert alert-success" t-out="state.statusMessage"/>
        </div>

        <BootstrapDialog identifier="'wifi-configuration'" btnName="'Configure'" onOpen.bind="getWiFiNetworks" onClose.bind="onClose">
            <t t-set-slot="header">
                Configure Wi-Fi
            </t>
            <t t-set-slot="body">
                <div t-if="this.state.scanning" class="position-absolute top-0 start-0 bg-white h-100 w-100 justify-content-center align-items-center d-flex flex-column gap-3 always-on-top">
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
                            <option t-foreach="this.state.availableWiFi.filter((wifi) => wifi)" t-as="wifi" t-key="wifi" t-att-value="wifi">
                                <t t-esc="wifi"/>
                            </option>
                        </select>
                        <small t-if="this.form.essid == 'Select Network...'" class="text-danger">Please select a network</small>
                    </div>

                    <div class="mb-3">
                        <input name="password" type="password" class="form-control" aria-label="Username" aria-describedby="basic-addon1" t-model="this.form.password" placeholder="Wi-Fi password"/>
                    </div>

                    <div class="d-flex justify-content-end gap-2">
                        <button t-if="this.isCurrentlyConnectedToWifi()" type="submit" class="btn btn-secondary btn-sm" t-on-click="clearConfiguration">
                            Disconnect From Current
                        </button>
                        <button type="submit" class="btn btn-primary btn-sm" t-on-click="connectToWiFi">Connect</button>
                    </div>
                </div>
            </t>
            <t t-set-slot="footer">
                <button type="button" class="btn btn-primary btn-sm" data-bs-dismiss="modal">Close</button>
            </t>
        </BootstrapDialog>
    `;
}
