/* global owl */

import useStore from "../../hooks/useStore.js";
import { BootstrapDialog } from "./BootstrapDialog.js";
import { LoadingFullScreen } from "../LoadingFullScreen.js";

const { Component, xml, useState, markup } = owl;

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

    async getUpgradeData() {
        try {
            const data = await this.store.rpc({
                url: "/hw_posbox_homepage/upgrade",
            });

            this.state.upgradeData = data;
            this.state.commitHtml = markup(data.commit);
            this.state.initialization = false;
        } catch {
            console.warn("Error while fetching data");
        }
    }

    async upgradeIotBox() {
        console.warn("Not implemented yet");
    }

    static template = xml`
        <LoadingFullScreen t-if="this.state.waitRestart">
            <t t-set-slot="body">
                Upgrading your device, please wait...
            </t>
        </LoadingFullScreen>

        <BootstrapDialog identifier="'update-configuration'" btnName="'Update'" onOpen.bind="getUpgradeData" onClose.bind="onClose">
            <t t-set-slot="header">
                Upgrade IoTBox
            </t>
            <t t-set-slot="body">
                <div t-if="this.state.initialization" class="position-absolute top-0 start-0 bg-white h-100 w-100 justify-content-center align-items-center d-flex flex-column gap-3" style="z-index: 9999">
                    <div class="spinner-border" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p>Currently fetching upgrade data...</p>
                </div>

                <div class="alert alert-warning fs-6" role="alert">
                    This tool will help you perform an upgrade of the IoTBox's software over the internet.
                    However the preferred method to upgrade the IoTBox is to flash the sd-card with the latest image.
                    The upgrade procedure is explained into to the IoTBox manual.<br/><br/>
                    Usefull links:
                    <ul>
                        <li>
                            <a href="https://nightly.odoo.com/master/iotbox/iotbox-latest.zip">Download the latest image</a>
                        </li>
                        <li>
                            <a href="https://www.odoo.com/documentation/17.0/applications/productivity/iot.html">IoTBox manual</a>
                        </li>
                    </ul>
                </div>

                <div class="bg-light rounded p-2 fs-6">
                    <h6>Commit details:</h6>
                    <pre t-out="this.state.commitHtml" />
                </div>

                <div class="w-100 mt-3 d-flex justify-content-center">
                    <button class="btn btn-primary btn-sm" t-on-click="upgradeIotBox">
                        Upgrade to <t t-esc="this.state.upgradeData.flashToVersion" />
                    </button>
                </div>
            </t>
            <t t-set-slot="footer">
                <button type="button" class="btn btn-primary btn-sm" data-bs-dismiss="modal">Close</button>
            </t>
        </BootstrapDialog>
    `;
}
