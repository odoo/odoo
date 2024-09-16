/* global owl */

import useStore from "../../hooks/useStore.js";
import { LoadingFullScreen } from "../LoadingFullScreen.js";
import { BootstrapDialog } from "./BootstrapDialog.js";

const { Component, xml, useState } = owl;

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
        });
    }

    async generatePassword() {
        try {
            this.state.loading = true;

            const data = await this.store.rpc({
                url: "/hw_posbox_homepage/generate_password",
            });

            this.state.password = data.password;
            this.state.loading = false;
        } catch {
            console.warn("Error while fetching data");
        }
    }

    async connectToRemoteDebug() {
        if (!this.state.ngrokToken) {
            return;
        }

        try {
            const data = await this.store.rpc({
                url: "/hw_posbox_homepage/enable_ngrok",
                method: "POST",
                params: {
                    auth_token: this.state.ngrokToken,
                },
            });

            if (data.status === "success") {
                this.state.ngrok = true;
            }
        } catch {
            console.warn("Error while enabling remote debugging");
        }
    }

    async restartIotBox() {
        try {
            await this.store.rpc({
                url: "/hw_posbox_homepage/restart_iotbox",
            });

            this.state.waitRestart = true;
        } catch {
            console.warn("Error while restarting IoT Box");
        }
    }

    static template = xml`
        <LoadingFullScreen t-if="this.state.waitRestart">
            <t t-set-slot="body">
                Processing your request, please wait...
            </t>
        </LoadingFullScreen>

        <BootstrapDialog identifier="'remote-debug-configuration'" btnName="'Remote debug'">
            <t t-set-slot="header">
                Remote Debugging
            </t>
            <t t-set-slot="body">
                <div class="alert alert-warning fs-6" role="alert">
                    This allows someone who give a ngrok authtoken to gain remote access to your IoT Box,
                    and thus your entire local network. Only enable this for someone you trust.
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
                <div class="d-flex justify-content-end gap-2">
                    <button type="submit" class="btn btn-primary mt-2 btn-sm" t-on-click="connectToRemoteDebug">Enable remote debugging</button>
                </div>
                <div t-if="this.state.ngrok" class="alert alert-success fs-6 mt-2" role="alert">
                    Your IoT Box is now accessible from the internet.
                </div>
            </t>
            <t t-set-slot="footer">
                <button type="submit" class="btn btn-danger btn-sm" t-on-click="restartIotBox">Restart IOT Box</button>
                <button type="button" class="btn btn-primary btn-sm" data-bs-dismiss="modal">Close</button>
            </t>
        </BootstrapDialog>
    `;
}
