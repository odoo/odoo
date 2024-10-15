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
        this.state = useState({ waitRestart: false });
        this.form = useState({
            token: "",
            iotname: this.store.base.hostname,
        });
    }

    async connectToServer() {
        try {
            const data = await this.store.rpc({
                url: "/hw_posbox_homepage/connect_to_server",
                method: "POST",
                params: this.form,
            });

            if (data.status === "success") {
                this.state.waitRestart = true;
            }
        } catch {
            console.warn("Error while fetching data");
        }
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
                Processing your request please wait...
            </t>
        </LoadingFullScreen>

        <BootstrapDialog identifier="'server-configuration'" btnName="'Configure'">
            <t t-set-slot="header">
                Configure Odoo Server
            </t>
            <t t-set-slot="body">
                <div class="alert alert-warning fs-6" role="alert">
                    Paste the token from the Connect wizard in your Odoo instance in the Server Token field.
                    If you change the IoT Box Name, your IoT Box will need a reboot.
                </div>
                <div class="mt-3">
                    <div class="input-group-sm mb-3" t-if="this.store.isLinux">
                        <label for="iotname">IoT Name</label>
                        <input name="iotname" type="text" class="form-control" t-model="this.form.iotname" />
                        <small t-if="!this.form.iotname" class="text-danger">Please enter a correct name</small>
                    </div>
                    <div class="input-group-sm mb-3">
                        <label for="token">Server Token</label>
                        <input name="token" type="text" class="form-control" t-model="this.form.token" />
                        <small t-if="!this.form.token" class="text-danger">Please enter a server token</small>
                    </div>
                    <div class="d-flex justify-content-end gap-2">
                        <button type="submit" class="btn btn-warning btn-sm" t-on-click="connectToServer">Connect</button>
                    </div>
                </div>
            </t>
            <t t-set-slot="footer">
                <div class="d-flex justify-content-between w-100">
                    <div style="font-size: 13px;">
                        <p class="m-0">Your current server is:<br/> <strong t-esc="this.store.base.server_status" /></p>
                    </div>
                    <div class="d-flex gap-2">
                        <button class="btn btn-danger btn-sm" t-on-click="clearConfiguration">Clear configuration</button>
                        <button type="button" class="btn btn-primary btn-sm" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </t>
        </BootstrapDialog>
    `;
}
