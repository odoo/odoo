/* global owl */

import useStore from "../../hooks/useStore.js";
import { LoadingFullScreen } from "../LoadingFullScreen.js";
import { BootstrapDialog } from "./BootstrapDialog.js";

const { Component, xml, onWillStart, useState } = owl;

export class RemoteDebugDialog extends Component {
    static props = {};
    static components = { BootstrapDialog, LoadingFullScreen };

    setup() {
        this.store = useStore();
        this.state = useState({
            password: "",
            loading: false,
            ngrok: false,
            ngrokToken: "",
            loadingNgrok: false,
        });

        onWillStart(async () => {
            await this.isNgrokEnabled();
        });
    }

    async isNgrokEnabled() {
        try {
            const data = await this.store.rpc({ url: "/iot_drivers/is_ngrok_enabled" });
            this.state.ngrok = data.enabled;
            if (!this.state.ngrok) {
                this.state.ngrokToken = "";
            }
        } catch {
            console.warn("Error while fetching data");
        }
    }

    async generatePassword() {
        try {
            this.state.loading = true;

            const data = await this.store.rpc({
                url: "/iot_drivers/generate_password",
                method: "POST",
            });

            this.state.password = data.password;
            this.state.loading = false;
        } catch {
            console.warn("Error while fetching data");
        }
    }

    async enableNgrok() {
        if (!this.state.ngrokToken) {
            return;
        }
        this.state.loadingNgrok = true;
        try {
            await this.store.rpc({
                url: "/iot_drivers/enable_ngrok",
                method: "POST",
                params: {
                    auth_token: this.state.ngrokToken,
                },
            });
            // Wait 2 seconds to let odoo-ngrok service start
            await new Promise((resolve) => setTimeout(resolve, 2000));
            await this.isNgrokEnabled();
        } catch {
            console.warn("Error while enabling remote debugging");
        }
        this.state.loadingNgrok = false;
    }

    async disableNgrok() {
        this.state.loadingNgrok = true;
        try {
            await this.store.rpc({
                url: "/iot_drivers/disable_ngrok",
                method: "POST",
            });
            // Wait 2 seconds to let odoo-ngrok service stop
            await new Promise((resolve) => setTimeout(resolve, 2000));
            await this.isNgrokEnabled();
        } catch {
            console.warn("Error while disabling remote debugging");
        }
        this.state.loadingNgrok = false;
    }

    static template = xml`
    <t t-translation="off">
        <BootstrapDialog identifier="'remote-debug-configuration'" btnName="'Remote debug'">
            <t t-set-slot="header">
                Remote Debugging
            </t>
            <t t-set-slot="body">
                <div t-if="!state.ngrok" class="alert alert-warning fs-6" role="alert">
                    This allows someone who give a ngrok authtoken to gain remote access to your IoT Box,
                    and thus your entire local network. Only enable this for someone you trust.
                </div>
                <div t-else="" class="alert alert-danger fs-6" role="alert">
                    Your IoT Box is currently accessible from the internet. 
                    The owner of the ngrok authtoken can access both the IoT Box and your local network.
                </div>
                <div class="d-flex flex-row gap-2 mb-4">
                    <input placeholder="Password" t-att-value="this.state.password" class="form-control" readonly="readonly" />
                    <button class="btn btn-primary btn-sm" t-on-click="generatePassword">
                        <div t-if="this.state.loading" class="spinner-border spinner-border-sm" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <t t-else="">Generate</t>
                    </button>
                </div>
                <input t-model="this.state.ngrokToken" placeholder="Authentication token" class="form-control" />
            </t>
            <t t-set-slot="footer">
                <button
                    type="submit"
                    class="btn btn-sm"
                    t-att-class="state.ngrok ? 'btn-primary' : 'btn-secondary'"
                    t-on-click="state.ngrok ? disableNgrok : enableNgrok"
                >
                    <div t-if="state.loadingNgrok" class="spinner-border spinner-border-sm" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <t t-else="">
                        <t t-esc="state.ngrok ? 'Disable remote debugging' : 'Enable remote debugging'" />
                    </t>
                </button>
                <button type="button" t-att-class="'btn btn-sm btn-' + (state.ngrok ? 'secondary' : 'primary')" data-bs-dismiss="modal">Close</button>
            </t>
        </BootstrapDialog>
    </t>
    `;
}
