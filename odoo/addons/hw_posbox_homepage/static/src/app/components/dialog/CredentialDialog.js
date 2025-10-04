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
                url: "/hw_posbox_homepage/save_credential",
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
                url: "/hw_posbox_homepage/clear_credential",
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
                Your IoT Box is currently processing your request. Please wait.
            </t>
        </LoadingFullScreen>

        <BootstrapDialog identifier="'credential-configuration'" btnName="'Credential'">
            <t t-set-slot="header">
                Configure credential
            </t>
            <t t-set-slot="body">
                <div class="alert alert-info fs-6" role="alert">
                    Set the DB UUID and your Contract Number you want to use.
                </div>
                <div class="mt-3">
                    <div class="input-group-sm mb-3">
                        <label for="iotname">DB uuid</label>
                        <input name="iotname" type="text" class="form-control" t-model="this.form.db_uuid" />
                        <small t-if="!this.form.db_uuid" class="text-danger">Please enter a correct db UUID</small>
                    </div>
                    <div class="input-group-sm mb-3">
                        <label for="token">Contract number</label>
                        <input name="token" type="text" class="form-control" t-model="this.form.enterprise_code" />
                        <small t-if="!this.form.enterprise_code" class="text-danger">Please enter a contract number</small>
                    </div>
                    <div class="d-flex justify-content-end gap-2">
                        <button type="submit" class="btn btn-warning btn-sm" t-on-click="connectToServer">Connect</button>
                    </div>
                </div>
            </t>
            <t t-set-slot="footer">
                <button class="btn btn-danger btn-sm" t-on-click="clearConfiguration">Clear configuration</button>
                <button type="button" class="btn btn-primary btn-sm" data-bs-dismiss="modal">Close</button>
            </t>
        </BootstrapDialog>
    `;
}
