/* global owl */

import useStore from "../../hooks/useStore.js";
import { BootstrapDialog } from "./BootstrapDialog.js";
import { LoadingFullScreen } from "../LoadingFullScreen.js";

const { Component, xml, useState, toRaw } = owl;

export class CredentialDialog extends Component {
    static props = {};
    static components = { BootstrapDialog, LoadingFullScreen };

    setup() {
        this.store = toRaw(useStore());
        this.state = useState({ waitRestart: false });
        this.form = useState({
            db_uuid: this.store.base.db_uuid,
            enterprise_code: "",
        });
    }

    async connectToServer() {
        try {
            if (!this.form.db_uuid || !this.form.enterprise_code) {
                return;
            }

            const data = await this.store.rpc({
                url: "/iot_drivers/save_credential",
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
                url: "/iot_drivers/clear_credential",
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

        <BootstrapDialog identifier="'credential-configuration'" btnName="'Credentials'">
            <t t-set-slot="header">
                Configure Credentials
            </t>
            <t t-set-slot="body">
                <div class="alert alert-info fs-6" role="alert">
                    Set the Database UUID and your Contract Number you want to use to validate your subscription.
                </div>
                <div class="d-flex flex-column gap-2 mt-3">
                    <input type="text" class="form-control" placeholder="Database UUID" t-model="form.db_uuid"/>
                    <input type="text" class="form-control" placeholder="Odoo contract number" t-model="form.enterprise_code"/>
                </div>
            </t>
            <t t-set-slot="footer">
                <button type="submit" class="btn btn-primary btn-sm" t-att-disabled="!form.db_uuid" t-on-click="connectToServer">Connect</button>
                <button class="btn btn-secondary btn-sm" t-on-click="clearConfiguration">Clear configuration</button>
                <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Close</button>
            </t>
        </BootstrapDialog>
    </t>
    `;
}
