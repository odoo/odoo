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
            loading: false,
            waitRestart: false,
            odooIsUpToDate: false,
            imageIsUpToDate: false,
            currentCommitHash: "",
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
            this.state.currentCommitHash = data.currentCommitHash;
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

    get everythingIsUpToDate() {
        return this.state.odooIsUpToDate && this.state.imageIsUpToDate;
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
                    Update
                    <a href="https://www.odoo.com/documentation/18.0/applications/general/iot/config/updating_iot.html" class="fa fa-question-circle text-decoration-none text-dark" target="_blank"></a>
                </div>
            </t>
            <t t-set-slot="body">
                <div t-if="this.state.initialization" class="position-absolute top-0 start-0 bg-white h-100 w-100 justify-content-center align-items-center d-flex flex-column gap-3 always-on-top">
                    <div class="spinner-border" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p>Currently fetching update data...</p>
                </div>

                <div class="mb-3">
                    <h6>Operating System Update</h6>
                    <div t-if="this.state.imageIsUpToDate" class="text-success px-2 small">
                        Operating system is up to date
                    </div>
                    <div t-else="" class="alert alert-warning small mb-0">
                        A new version of the operating system is available, see:
                        <a href="https://www.odoo.com/documentation/18.0/applications/general/iot/config/updating_iot.html#flashing-the-sd-card-on-iot-box" target="_blank" class="alert-link">
                            Flashing the SD Card on IoT Box
                        </a>
                    </div>
                    <div t-if="this.store.dev" class="alert alert-light small">
                        <a href="https://nightly.odoo.com/master/iotbox/" target="_blank" class="alert-link">
                            Current: <t t-esc="this.store.base.version"/>
                        </a>
                    </div>
                </div>

                <div class="mb-3">
                    <h6>IoT Box Update</h6>
                    <div t-if="this.state.odooIsUpToDate" class="text-success px-2 small">
                        IoT Box is up to date.
                    </div>
                    <div t-else="" class="d-flex justify-content-between align-items-center alert alert-warning small">
                        A new version of the IoT Box is available
                        <button class="btn btn-primary btn-sm" t-on-click="updateGitTree">Update</button>
                    </div>
                    <div t-if="this.store.dev" class="alert alert-light small">
                        Current: 
                        <a t-att-href="'https://github.com/odoo/odoo/commit/' + this.state.currentCommitHash" target="_blank" class="alert-link">
                            <t t-esc="this.state.currentCommitHash"/>
                        </a>
                    </div>
                </div>

                <h6>Drivers Update</h6>
                <div class="d-flex gap-2">
                    <button class="btn btn-secondary btn-sm" t-on-click="forceUpdateIotHandlers">
                        Force Drivers Update
                    </button>
                </div>
            </t>
            <t t-set-slot="footer">
                <button 
                    type="button"
                    t-att-class="'btn btn-sm ' + (this.everythingIsUpToDate ? 'btn-primary' : 'btn-secondary')"
                    data-bs-dismiss="modal">
                    Close
                </button>
            </t>
        </BootstrapDialog>
    `;
}
