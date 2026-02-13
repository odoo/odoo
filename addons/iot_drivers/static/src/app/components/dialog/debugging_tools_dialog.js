/* global owl */

import useStore from "../../hooks/store_hook.js";
import { LoadingFullScreen } from "../loading_full_screen.js";
import { Dialog } from "./dialog.js";

const { Component, xml, onWillStart, signal } = owl;

export class DebuggingToolsDialog extends Component {
    static components = { Dialog, LoadingFullScreen };

    store = useStore();

    password = signal("");
    loading = signal(false);
    remoteDebug = signal(false);
    remoteDebugToken = signal("");
    loadingRemoteDebug = signal(false);

    setup() {
        onWillStart(async () => {
            await this.isRemoteDebugEnabled();
        });
    }

    async isRemoteDebugEnabled() {
        try {
            const data = await this.store.rpc({ url: "/iot_drivers/is_remote_debug_enabled" });
            this.remoteDebug.set(data.enabled);
            if (!this.remoteDebug()) {
                this.remoteDebugToken.set("");
            }
        } catch {
            console.warn("Error while fetching data");
        }
    }

    async generatePassword() {
        try {
            this.loading.set(true);

            const data = await this.store.rpc({
                url: "/iot_drivers/generate_password",
                method: "POST",
            });

            this.password.set(data.password);
            this.loading.set(false);
        } catch {
            console.warn("Error while fetching data");
        }
    }

    async enableRemoteDebug() {
        if (!this.remoteDebugToken()) {
            return;
        }
        this.loadingRemoteDebug.set(true);
        try {
            await this.store.rpc({
                url: "/iot_drivers/enable_remote_debug",
                method: "POST",
                params: {
                    auth_token: this.remoteDebugToken(),
                },
            });
            // Wait 2 seconds to let remote debug start
            await new Promise((resolve) => setTimeout(resolve, 2000));
            await this.isRemoteDebugEnabled();
        } catch {
            console.warn("Error while enabling remote debugging");
        }
        this.loadingRemoteDebug.set(false);
    }

    async disableRemoteDebug() {
        this.loadingRemoteDebug.set(true);
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
        this.loadingRemoteDebug.set(false);
    }

    static template = xml`
    <t t-translation="off">
        <Dialog
            name="'Debugging Tools'"
            help="'https://www.odoo.com/documentation/latest/applications/general/iot/iot_advanced/ssh_connect.html'"
            btnName="'Debugging Tools'">
            <t t-set-slot="body">
                <h6>Remote Debug</h6>
                <div t-if="!this.remoteDebug()" class="alert alert-warning fs-6" role="alert">
                    This allows someone who give a Tailscale authentication key to gain remote access to your IoT Box,
                    and thus your entire local network. Only enable this for someone you trust.
                </div>
                <div t-else="" class="alert alert-danger fs-6" role="alert">
                    Your IoT Box is currently accessible from the internet. 
                    The owner of the Tailscale authentication key can access both the IoT Box and your local network.
                </div>
                <div class="d-flex flex-row gap-2 mb-4">
                    <input t-model="this.remoteDebugToken" placeholder="Authentication key" class="form-control" t-att-disabled="this.remoteDebug()"/>
                    <button
                        type="submit"
                        class="btn btn-sm"
                        t-att-class="this.remoteDebug() ? 'btn-primary' : 'btn-secondary'"
                        t-on-click="this.remoteDebug() ? this.disableRemoteDebug : this.enableRemoteDebug"
                    >
                    <div t-if="this.loadingRemoteDebug()" class="spinner-border spinner-border-sm" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <t t-else="" t-out="this.remoteDebug() ? 'Disable' : 'Enable'" />
                </button>
                </div>

                <h6 class="mt-3">System password</h6>
                <div class="d-flex flex-row gap-2 mb-4">
                    <input placeholder="Password" t-att-value="this.password()" class="form-control" readonly="readonly" />
                    <button class="btn btn-secondary btn-sm" t-on-click="this.generatePassword">
                        <div t-if="this.loading()" class="spinner-border spinner-border-sm" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <t t-else="">Generate</t>
                    </button>
                </div>
            </t>
            <t t-set-slot="footer">
                <button type="button" t-att-class="'btn btn-sm btn-' + (this.remoteDebug() ? 'secondary' : 'primary')" data-bs-dismiss="modal">Close</button>
            </t>
        </Dialog>
    </t>
    `;
}
