/* global owl */

import useStore from "../../hooks/store_hook.js";
import { Dialog } from "./dialog.js";
import { LoadingFullScreen } from "../loading_full_screen.js";

const { Component, xml, useState, toRaw } = owl;

export class SixTerminalDialog extends Component {
    static props = {};
    static components = { Dialog, LoadingFullScreen };

    setup() {
        this.store = toRaw(useStore());
        this.state = useState({ waitRestart: false });
        this.form = useState({ terminal_id: this.store.base.six_terminal });
    }

    async configureSix() {
        try {
            if (!this.form.terminal_id) {
                return;
            }

            const data = await this.store.rpc({
                url: "/iot_drivers/six_payment_terminal_add",
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

    async disconnectSix() {
        try {
            const data = await this.store.rpc({
                url: "/iot_drivers/six_payment_terminal_clear",
            });

            if (data.status === "success") {
                this.state.waitRestart = true;
            }
        } catch {
            console.warn("Error while clearing configuration");
        }
    }

    static template = xml`
    <t t-translation="off">
        <LoadingFullScreen t-if="this.state.waitRestart">
            <t t-set-slot="body">
                Your IoT Box is currently processing your request. Please wait.
            </t>
        </LoadingFullScreen>

        <Dialog
            name="'Configure a Six Terminal'"
            help="'https://www.odoo.com/documentation/latest/applications/sales/point_of_sale/payment_methods/terminals/six.html'"
            btnName="'Configure'">
            <t t-set-slot="body">
                <div class="alert alert-info fs-6" role="alert">
                    Set the Terminal ID (TID) of the terminal you want to use.
                </div>
                <div class="mt-3">
                    <div class="input-group-sm mb-3">
                        <input type="text" class="form-control" placeholder="Six Terminal ID (digits only)" t-model="this.form.terminal_id" />
                    </div>
                </div>
            </t>
            <t t-set-slot="footer">
                <button type="submit" class="btn btn-primary btn-sm" t-att-disabled="!form.terminal_id" t-on-click="configureSix">Configure</button>
                <button class="btn btn-secondary btn-sm" t-on-click="disconnectSix">Disconnect current</button>
                <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Close</button>
            </t>
        </Dialog>
    </t>
    `;
}
