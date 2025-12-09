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
            remoteDebug: false,
            remoteDebugToken: "",
            loadingRemoteDebug: false,
        });

        onWillStart(async () => {
            await this.isRemoteDebugEnabled();
        });
    }

    async isRemoteDebugEnabled() {
        try {
            const data = await this.store.rpc({ url: "/iot_drivers/is_remote_debug_enabled" });
            this.state.remoteDebug = data.enabled;
            if (!this.state.remoteDebug) {
                this.state.remoteDebugToken = "";
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

    async enableRemoteDebug() {
        if (!this.state.remoteDebugToken) {
            return;
        }
        this.state.loadingRemoteDebug = true;
        try {
            await this.store.rpc({
                url: "/iot_drivers/enable_remote_debug",
                method: "POST",
                params: {
                    auth_token: this.state.remoteDebugToken,
                },
            });
            // Wait 2 seconds to let remote debug start
            await new Promise((resolve) => setTimeout(resolve, 2000));
            await this.isRemoteDebugEnabled();
        } catch {
            console.warn("Error while enabling remote debugging");
        }
        this.state.loadingRemoteDebug = false;
    }

    async disableRemoteDebug() {
        this.state.loadingRemoteDebug = true;
        try {
            await this.store.rpc({
                url: "/iot_drivers/disable_remote_debug",
                method: "POST",
            });
            // Wait 2 seconds to let remote debug stop
            await new Promise((resolve) => setTimeout(resolve, 2000));
            await this.isRemoteDebugEnabled();
        } catch {
            console.warn("Error while disabling remote debugging");
        }
        this.state.loadingRemoteDebug = false;
    }

    static template = xml`
    <t t-translation="off">
        <BootstrapDialog identifier="'remote-debug-configuration'" btnName="'Debugging Tools'">
            <t t-set-slot="header">
                Debugging Tools
            </t>
            <t t-set-slot="body">
                <h6>Remote Debug</h6>
                <div t-if="!state.remoteDebug" class="alert alert-warning fs-6" role="alert">
                    This allows someone who give a Tailscale authentication key to gain remote access to your IoT Box,
                    and thus your entire local network. Only enable this for someone you trust.
                </div>
                <div t-else="" class="alert alert-danger fs-6" role="alert">
                    Your IoT Box is currently accessible from the internet. 
                    The owner of the Tailscale authentication key can access both the IoT Box and your local network.
                </div>
                <div class="d-flex flex-row gap-2 mb-4">
                    <input t-model="this.state.remoteDebugToken" placeholder="Authentication key" class="form-control" t-att-disabled="state.remoteDebug"/>
                    <button
                        type="submit"
                        class="btn btn-sm"
                        t-att-class="state.remoteDebug ? 'btn-primary' : 'btn-secondary'"
                        t-on-click="state.remoteDebug ? disableRemoteDebug : enableRemoteDebug"
                    >
                    <div t-if="state.loadingRemoteDebug" class="spinner-border spinner-border-sm" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <t t-else="" t-esc="state.remoteDebug ? 'Disable' : 'Enable'" />
                </button>
                </div>

                <h6 class="mt-3">System password</h6>
                <div class="d-flex flex-row gap-2 mb-4">
                    <input placeholder="Password" t-att-value="this.state.password" class="form-control" readonly="readonly" />
                    <button class="btn btn-secondary btn-sm" t-on-click="generatePassword">
                        <div t-if="this.state.loading" class="spinner-border spinner-border-sm" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <t t-else="">Generate</t>
                    </button>
                </div>
            </t>
            <t t-set-slot="footer">
                <button type="button" t-att-class="'btn btn-sm btn-' + (state.remoteDebug ? 'secondary' : 'primary')" data-bs-dismiss="modal">Close</button>
            </t>
        </BootstrapDialog>
    </t>
    `;
}
