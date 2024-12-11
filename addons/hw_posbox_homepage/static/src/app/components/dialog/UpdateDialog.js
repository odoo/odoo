/* global owl */

import useStore from "../../hooks/useStore.js";
import { BootstrapDialog } from "./BootstrapDialog.js";
import { LoadingFullScreen } from "../LoadingFullScreen.js";

const { Component, xml, useState } = owl;

export class UpdateDialog extends Component {
    static props = {};
    static components = { BootstrapDialog, LoadingFullScreen };

    setup() {
        this.store = useStore();
        this.state = useState({
            initialization: true,
            commitHtml: "",
            loading: false,
            waitRestart: false,
            upgradeData: [],
        });
    }

    onClose() {
        this.state.initialization = [];
    }

    async getVersionInfo() {
        try {
            const data = await this.store.rpc({
                url: "/hw_posbox_homepage/version_info",
            });

            this.state.odooIsUpToDate = data.odooIsUpToDate;
            this.state.imageIsUpToDate = data.imageIsUpToDate;
            this.state.initialization = false;
        } catch {
            console.warn("Error while fetching version info");
        }
    }

    async updateGitTree() {
        this.state.waitRestart = true;
        try {
            const data = await this.store.rpc({
                url: "/hw_posbox_homepage/update_git_tree",
                method: "POST",
            });
            if (data.status === "success") {
                this.state.isUpToDate = true;
            }
        } catch {
            console.warn("Error while updating IoT Box.");
        }
    }

    async forceUpdateIotHandlers() {
        this.state.waitRestart = true;
        try {
            await this.store.rpc({
                url: "/hw_posbox_homepage/load_iot_handlers",
            });
        } catch {
            console.warn("Error while downloading handlers from db.");
        }
    }

    static template = xml`
        <LoadingFullScreen t-if="this.state.waitRestart">
            <t t-set-slot="body">
                Updating your device, please wait...
            </t>
        </LoadingFullScreen>

        <BootstrapDialog identifier="'update-configuration'" btnName="'Update'" onOpen.bind="getVersionInfo" onClose.bind="onClose">
            <t t-set-slot="header">
                <div>
                    Update IoT Box
                    <a href="https://www.odoo.com/documentation/18.0/applications/general/iot/config/updating_iot.html" class="fa fa-question-circle text-decoration-none text-dark" target="_blank"></a>
                </div>
            </t>
            <t t-set-slot="body">
                <div t-if="this.state.initialization" class="position-absolute top-0 start-0 bg-white h-100 w-100 justify-content-center align-items-center d-flex flex-column gap-3" style="z-index: 9999">
                    <div class="spinner-border" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p>Currently fetching update data...</p>
                </div>

                <h6>System Image</h6>
                <div t-if="this.state.imageIsUpToDate" class="alert alert-success">
                    <h7>System is up to date! (<t t-esc="this.store.base.version"/>)</h7>
                </div>
                <div t-else="" class="alert alert-warning">
                    <h7>A new image is available!</h7>
                    <div>
                        See:
                        <a href="https://www.odoo.com/documentation/18.0/applications/general/iot/config/updating_iot.html#flashing-the-sd-card-on-iot-box" target="_blank" class="alert-link">
                            Flashing the SD Card on IoT Box
                        </a>
                    </div>
                </div>

                <h6>Odoo Service</h6>
                <div t-if="this.state.odooIsUpToDate" class="alert alert-success">
                    <h7>Service is up to date!</h7>
                </div>
                <div t-else="" class="d-flex justify-content-between align-items-center alert alert-warning">
                    <h7>An update is available!</h7>
                    <button class="btn btn-primary btn-sm" t-on-click="updateGitTree">Update</button>
                </div>

                <h6>IoT Handlers</h6>
                <div class="d-flex gap-2">
                    <button class="btn btn-primary btn-sm" t-on-click="forceUpdateIotHandlers">
                        Force Update Handlers
                    </button>
                </div>
            </t>
            <t t-set-slot="footer">
                <button type="button" class="btn btn-primary btn-sm" data-bs-dismiss="modal">Close</button>
            </t>
        </BootstrapDialog>
    `;
}
