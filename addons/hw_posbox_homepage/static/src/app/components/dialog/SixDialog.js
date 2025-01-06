/* global owl */

import useStore from "../../hooks/useStore.js";
import { BootstrapDialog } from "./BootstrapDialog.js";
import { LoadingFullScreen } from "../LoadingFullScreen.js";

const { Component, xml, useState, toRaw } = owl;

export class SixDialog extends Component {
    static props = {};
    static components = { BootstrapDialog, LoadingFullScreen };

    setup() {
        this.store = toRaw(useStore());
        this.state = useState({ waitRestart: false });
        this.form = useState({ terminal_id: this.store.base.six_terminal });
    }

    async connectToServer() {
        try {
            if (!this.form.terminal_id) {
                return;
            }

            const data = await this.store.rpc({
                url: "/hw_posbox_homepage/six_payment_terminal_add",
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
                url: "/hw_posbox_homepage/six_payment_terminal_clear",
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
                Your IoT System is currently processing your request. Please wait.
            </t>
        </LoadingFullScreen>

        <BootstrapDialog identifier="'six-configuration'" btnName="'Configure'">
            <t t-set-slot="header">
                Configure Six Terminal
            </t>
            <t t-set-slot="body">
                <div class="alert alert-warning fs-6" role="alert">
                    Set the Terminal ID (TID) of the terminal you want to use.
                </div>
                <div class="mt-3">
                    <div class="input-group-sm mb-3">
                        <label for="iotname">Terminal ID (Digit only)</label>
                        <input name="iotname" type="text" class="form-control" t-model="this.form.terminal_id" />
                        <small t-if="!this.form.terminal_id" class="text-danger">Please enter a correct terminal ID</small>
                    </div>
                    <div class="d-flex justify-content-end gap-2">
                        <button class="btn btn-danger btn-sm" t-on-click="clearConfiguration">Clear configuration</button>
                        <button type="submit" class="btn btn-warning btn-sm" t-on-click="connectToServer">Connect</button>
                    </div>
                </div>
            </t>
            <t t-set-slot="footer">
                <button type="button" class="btn btn-primary btn-sm" data-bs-dismiss="modal">Close</button>
            </t>
        </BootstrapDialog>
    `;
}
