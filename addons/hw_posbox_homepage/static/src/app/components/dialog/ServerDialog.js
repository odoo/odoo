/* global owl */

import useStore from "../../hooks/useStore.js";
import { BootstrapDialog } from "./BootstrapDialog.js";
import { LoadingFullScreen } from "../LoadingFullScreen.js";

const { Component, xml, useState, toRaw } = owl;

export class ServerDialog extends Component {
    static props = {};
    static components = { BootstrapDialog, LoadingFullScreen };

    setup() {
        this.store = toRaw(useStore());
        this.state = useState({ waitRestart: false, loading: false, error: null });
        this.form = useState({ token: "" });
    }

    async connectToServer() {
        this.state.loading = true;
        this.state.error = null;
        try {
            const data = await this.store.rpc({
                url: "/hw_posbox_homepage/connect_to_server",
                method: "POST",
                params: this.form,
            });

            if (data.status === "success") {
                this.state.waitRestart = true;
            } else {
                this.state.error = data.message;
            }
        } catch {
            console.warn("Error while fetching data");
        }
        this.state.loading = false;
    }

    async clearConfiguration() {
        try {
            const data = await this.store.rpc({
                url: "/hw_posbox_homepage/server_clear",
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
                Updating Odoo Server information, please wait...
            </t>
        </LoadingFullScreen>

        <BootstrapDialog identifier="'server-configuration'" btnName="'Configure'">
            <t t-set-slot="header">
                Configure Odoo Server
            </t>
            <t t-set-slot="body">
                <div class="alert alert-warning fs-6 pb-0" role="alert">
                    <ol>
                        <li>Install <b>IoT App</b> on your database,</li>
                        <li>From the IoT App click on <b>Connect</b> button.</li>
                    </ol>
                </div>
                <div class="mt-3">
                    <div class="input-group-sm mb-3">
                        <input type="text" class="form-control" t-model="form.token" placeholder="Server token"/>
                    </div>
                    <div class="small" t-if="store.base.server_status">
                        <p class="m-0">
                            Your current server is: <br/> 
                            <strong t-esc="store.base.server_status" />
                        </p>
                    </div>
                </div>
            </t>
            <t t-set-slot="footer">
                <button type="submit" class="btn btn-primary btn-sm" t-att-disabled="state.loading or !form.token" t-on-click="connectToServer">Connect</button>
                <button type="button" class="btn btn-secondary btn-sm" t-if="store.base.server_status" t-on-click="clearConfiguration">Disconnect from current</button>
                <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Close</button>
            </t>
        </BootstrapDialog>
    `;
}
