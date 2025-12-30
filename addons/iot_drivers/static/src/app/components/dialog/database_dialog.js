/* global owl */

import useStore from "../../hooks/store_hook.js";
import { Dialog } from "./dialog.js";
import { LoadingFullScreen } from "../loading_full_screen.js";

const { Component, xml, useState } = owl;

export class DatabaseDialog extends Component {
    static props = {};
    static components = { Dialog, LoadingFullScreen };

    setup() {
        this.store = useStore();
        this.state = useState({ waitRestart: false, loading: false, error: null });
        this.form = useState({ token: "" });
    }

    async connectToServer() {
        this.state.loading = true;
        this.state.error = null;
        try {
            const data = await this.store.rpc({
                url: "/iot_drivers/connect_to_server",
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
        this.state.waitRestart = true;
        try {
            await this.store.rpc({
                url: "/iot_drivers/server_clear",
            });
        } catch {
            console.warn("Error while clearing configuration");
        }
    }

    static template = xml`
    <t t-translation="off">
        <LoadingFullScreen t-if="this.state.waitRestart">
            <t t-set-slot="body">
                Updating Odoo Server information, please wait...
            </t>
        </LoadingFullScreen>

        <Dialog
            name="'Configure Odoo Database'"
            help="'https://www.odoo.com/documentation/latest/applications/general/iot/connect.html'"
            btnName="'Configure'">
            <t t-set-slot="body">
                <div class="alert alert-warning fs-6 pb-0" role="alert" t-if="!store.base.server_status">
                    <ol>
                        <li>Install <b>IoT App</b> on your database,</li>
                        <li>From the IoT App click on <b>Connect</b> button.</li>
                    </ol>
                </div>
                <div class="mt-3">
                    <div class="input-group-sm mb-3" t-if="!store.base.server_status">
                        <input type="text" class="form-control" t-model="form.token" placeholder="Server token"/>
                    </div>
                    <div class="small" t-else="">
                        <p class="m-0">
                            Your current database is: <br/> 
                            <strong t-esc="store.base.server_status" />
                        </p>
                    </div>
                </div>
            </t>
            <t t-set-slot="footer">
                <button type="submit" class="btn btn-primary btn-sm" t-if="!store.base.server_status" t-on-click="connectToServer" t-att-disabled="state.loading or !form.token" >Connect</button>
                <button type="button" class="btn btn-danger btn-sm" t-if="store.base.server_status" t-on-click="clearConfiguration">Disconnect</button>
                <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Close</button>
            </t>
        </Dialog>
    </t>
    `;
}
