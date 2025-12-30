/* global owl */

import useStore from "../../hooks/store_hook.js";
import { Dialog } from "./dialog.js";
import { LoadingFullScreen } from "../loading_full_screen.js";

const { Component, xml, useState } = owl;

export class UpdateDialog extends Component {
    static props = {};
    static components = { Dialog, LoadingFullScreen };

    setup() {
        this.store = useStore();
        this.state = useState({
            waitRestart: false,
        });
    }

    async update() {
        this.state.waitRestart = true;
        try {
            const data = await this.store.rpc({
                url: "/iot_drivers/update_git_tree",
                method: "POST",
            });

            if (data.status === "error") {
                this.state.waitRestart = false;
                console.error(data.message);
            }
        } catch {
            console.warn("Error while updating IoT Box.");
        }
    }

    static template = xml`
    <t t-translation="off">
        <LoadingFullScreen t-if="this.state.waitRestart">
            <t t-set-slot="body">
                Updating your device, please wait...
            </t>
        </LoadingFullScreen>

        <Dialog
            name="'IoT Box update'"
            help="'https://www.odoo.com/documentation/latest/applications/general/iot/iot_advanced/updating_iot.html'"
            btnName="'Update'">
            <t t-set-slot="body">
                <div class="alert alert-info" role="alert">
                    The IoT Box is automatically updated <b>every Monday</b> at midnight. 
                </div>
                If you are experiencing issues that may have been fixed since the last update, you can manually trigger an update here.
            </t>
            <t t-set-slot="footer">
                <button type="button" class="btn btn-sm btn-primary" t-on-click="update">Update</button>
                <button type="button" class="btn btn-sm btn-secondary" data-bs-dismiss="modal">Close</button>
            </t>
        </Dialog>
    </t>
    `;
}
