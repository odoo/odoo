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
            loading: false,
            waitRestart: false,
            availableWifi: [],
        });
        this.form = useState({
            essid: "",
            password: "",
            persistent: false,
        });
    }

    onClose() {
        this.state.availableWifi = [];
        this.state.scanning = true;
        this.form.essid = "";
        this.form.password = "";
        this.form.persistent = false;
    }

    async getWifiNetworks() {
        try {
            const data = await this.store.rpc({
                url: "/hw_posbox_homepage/wifi",
            });

            this.state.availableWifi = data;
            this.state.scanning = false;
        } catch {
            console.warn("Error while fetching data");
        }
    }

    async connectToWifi() {
        if (!this.form.essid || !this.form.password) {
            return;
        }

        const data = await this.store.rpc({
            url: "/hw_posbox_homepage/update_wifi",
            method: "POST",
            params: this.form,
        });

        if (data.status === "success") {
            this.state.waitRestart = true;
        }
    }

    async clearConfiguration() {
        try {
            const data = await this.store.rpc({
                url: "/hw_posbox_homepage/wifi_clear",
            });

            if (data.status === "success") {
                this.state.waitRestart = true;
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

        <BootstrapDialog identifier="'wifi-configuration'" btnName="'Configure'" onOpen.bind="getWifiNetworks" onClose.bind="onClose">
            <t t-set-slot="header">
                Configure WIFI
            </t>
            <t t-set-slot="body">
                <div t-if="this.state.scanning" class="position-absolute top-0 start-0 bg-white h-100 w-100 justify-content-center align-items-center d-flex flex-column gap-3" style="z-index: 9999">
                    <div class="spinner-border" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p>Currently scanning for available networks...</p>
                </div>

                <div class="alert alert-warning fs-6" role="alert">
                    Here you can configure how the iotbox should connect to wireless networks.
                    Currently only Open and WPA networks are supported. When enabling the persistent checkbox,
                    the chosen network will be saved and the iotbox will attempt to connect to it every time it boots.
                </div>
                <div class="mt-3">
                    <div class="mb-3">
                        <label for="wifi-ssid">WIFI SSID</label>
                        <select name="essid" class="form-control" id="wifi-ssid" t-model="this.form.essid">
                            <option>Choose...</option>
                            <option t-foreach="this.state.availableWifi.filter((wifi) => wifi)" t-as="wifi" t-key="wifi" t-att-value="wifi">
                                <t t-esc="wifi" />
                            </option>
                        </select>
                        <small t-if="!this.form.essid" class="text-danger">Please select a network</small>
                    </div>

                    <div class="mb-3">
                        <label for="wifi-ssid">WIFI Password</label>
                        <input name="password" type="password" class="form-control" aria-label="Username" aria-describedby="basic-addon1" t-model="this.form.password" />
                        <small t-if="!this.form.password" class="text-danger">Please enter a password</small>
                    </div>

                    <div class="form-check">
                        <input name="persistent" class="form-check-input" type="checkbox" value="" id="persistent" t-model="this.form.persistent" />
                        <label class="form-check-label" for="persistent">
                            Persistent
                        </label>
                    </div>

                    <div class="d-flex justify-content-end gap-2">
                        <button type="submit" class="btn btn-danger btn-sm" t-on-click="clearConfiguration">Clear</button>
                        <button type="submit" class="btn btn-warning btn-sm" t-on-click="connectToWifi">Connect</button>
                    </div>
                </div>
            </t>
            <t t-set-slot="footer">
                <button type="button" class="btn btn-primary btn-sm" data-bs-dismiss="modal">Close</button>
            </t>
        </BootstrapDialog>
    `;
}
