/* global owl */

import useStore from "../../hooks/useStore.js";
import { BootstrapDialog } from "./BootstrapDialog.js";
import { LoadingFullScreen } from "../LoadingFullScreen.js";

const { Component, xml, useState, toRaw } = owl;

export class HostnameDialog extends Component {
    static props = {};
    static components = { BootstrapDialog, LoadingFullScreen };

    setup() {
        this.store = toRaw(useStore());
        this.state = useState({ waitRestart: false, loading: false, error: null });
        this.form = useState({
            hostname: this.store.base.hostname,
        });
    }

    async rename() {
        this.state.loading = true;
        this.state.error = null;
        try {
            const data = await this.store.rpc({
                url: "/hw_posbox_homepage/update_hostname",
                method: "POST",
                params: this.form,
            });

            if (data.status === "failure") {
                this.state.error = data.message;
            }
        } catch {
            console.debug("Error while fetching data: the server is most likely rebooting to apply the new hostname.");
            this.state.waitRestart = true;
        }
        this.state.loading = false;
    }

    static template = xml`
        <LoadingFullScreen t-if="this.state.waitRestart">
            <t t-set-slot="body">
                Your IoT Box is restarting to change its hostname, please wait...
            </t>
        </LoadingFullScreen>

        <BootstrapDialog identifier="'hostname-configuration'" btnName="'Configure'">
            <t t-set-slot="header">
                Change Hostname
            </t>
            <t t-set-slot="body">
                <div class="alert alert-warning fs-6" role="alert">
                    Renaming the IoT Box will restart the device.
                </div>
                <div class="mt-3">
                    <div class="input-group-sm mb-3" t-if="store.isLinux">
                        <input type="text" class="form-control" placeholder="IoT Box name" t-model="form.hostname" />
                    </div>
                </div>
            </t>
            <t t-set-slot="footer">
                <div class="d-flex gap-2">
                    <button type="submit" class="btn btn-primary btn-sm" t-att-disabled="state.loading or !form.hostname" t-on-click="rename">Rename</button>
                    <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Close</button>
                </div>
            </t>
        </BootstrapDialog>
    `;
}
