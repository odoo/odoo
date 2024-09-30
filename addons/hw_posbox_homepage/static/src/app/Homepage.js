/* global owl */

import { SingleData } from "./components/SingleData.js";
import { FooterButtons } from "./components/FooterButtons.js";
import { ServerDialog } from "./components/dialog/ServerDialog.js";
import { WifiDialog } from "./components/dialog/WifiDialog.js";
import useStore from "./hooks/useStore.js";
import { UpdateDialog } from "./components/dialog/UpdateDialog.js";
import { DeviceDialog } from "./components/dialog/DeviceDialog.js";
import { SixDialog } from "./components/dialog/SixDialog.js";
import { LoadingFullScreen } from "./components/LoadingFullScreen.js";
import { IconButton } from "./components/IconButton.js";

const { Component, xml, useState, onWillStart } = owl;

export class Homepage extends Component {
    static props = {};
    static components = {
        SingleData,
        FooterButtons,
        ServerDialog,
        WifiDialog,
        UpdateDialog,
        DeviceDialog,
        SixDialog,
        LoadingFullScreen,
        IconButton,
    };

    setup() {
        this.store = useStore();
        this.state = useState({ loading: true, waitRestart: false });
        this.data = useState({});
        this.store.advanced = localStorage.getItem("showAdvanced") === "true";

        onWillStart(async () => {
            await this.loadInitialData();
        });

        setInterval(() => {
            this.loadInitialData();
        }, 10000);
    }

    async loadInitialData() {
        try {
            const data = await this.store.rpc({
                url: "/hw_posbox_homepage/data",
            });
            this.data = data;
            this.store.base = data;
            this.state.loading = false;
            this.store.update = new Date().getTime();
        } catch {
            console.warn("Error while fetching data");
        }
    }

    async restartOdooService() {
        try {
            await this.store.rpc({
                url: "/hw_posbox_homepage/restart_odoo_service",
            });

            this.state.waitRestart = true;
        } catch {
            console.warn("Error while restarting Odoo Service");
        }
    }

    toggleAdvanced() {
        this.store.advanced = !this.store.advanced;
        localStorage.setItem("showAdvanced", this.store.advanced);
    }

    static template = xml`
    <LoadingFullScreen t-if="this.state.waitRestart">
        <t t-set-slot="body">
           Restarting IoT Box, please wait...
        </t>
    </LoadingFullScreen>

    <div t-if="!this.state.loading" class="w-100 d-flex flex-column align-items-center justify-content-center" style="background-color: #F1F1F1; height: 100vh">
        <div class="bg-white p-4 rounded overflow-auto position-relative" style="min-width: 600px;">
            <div class="position-absolute end-0 top-0 mt-3 me-4 d-flex gap-">
                <IconButton onClick.bind="toggleAdvanced" icon="this.store.advanced ? 'fa-cog' : 'fa-cogs'" />
                <IconButton onClick.bind="restartOdooService" icon="'fa-power-off'" />
            </div>
            <div class="d-flex mb-4 flex-column align-items-center justify-content-center">
                <h4 class="text-center m-0">IoT Box - <t t-esc="this.data.hostname" /></h4>
            </div>
            <div class="alert alert-warning" role="alert">
                <p class="m-0 fw-bold">HTTPS certificate</p>
                <small>Error code: <t t-esc="this.data.certificate_details" /></small>
            </div>
            <SingleData name="'Name'" value="this.data.hostname" icon="'fa-id-card'">
				<t t-set-slot="button">
					<ServerDialog t-if="this.store.isLinux" />
				</t>
			</SingleData>
            <SingleData t-if="this.store.advanced" name="'Version'" value="this.data.version" icon="'fa-microchip'">
                <t t-set-slot="button">
                    <UpdateDialog t-if="this.store.isLinux" />
                </t>
            </SingleData>
            <SingleData t-if="this.store.advanced" name="'IP address'" value="this.data.ip" icon="'fa-globe'" />
            <SingleData t-if="this.store.advanced" name="'MAC address'" value="this.data.mac.toUpperCase()" icon="'fa-address-card'" />
            <SingleData t-if="this.store.isLinux" name="'Internet Status'" value="this.data.network_status"  icon="'fa-wifi'">
                <t t-set-slot="button">
                    <WifiDialog />
                </t>
            </SingleData>
            <SingleData name="'Odoo database connected'" value="this.data.server_status" icon="'fa-link'">
				<t t-set-slot="button">
					<ServerDialog />
				</t>
			</SingleData>
            <SingleData t-if="this.data.pairing_code" name="'Pairing Code'" value="this.data.pairing_code" icon="'fa-code'"/>
            <SingleData  t-if="this.store.advanced" name="'Six terminal'" value="this.data.six_terminal" icon="'fa-money'">
                <t t-set-slot="button">
                    <SixDialog />
                </t>
            </SingleData>
            <SingleData name="'Devices'" value="this.data.iot_device_status.length + ' devices'" icon="'fa-plug'">
                <t t-set-slot="button">
                    <DeviceDialog />
                </t>
            </SingleData>

            <hr class="mt-5" />
            <FooterButtons />
            <div class="d-flex justify-content-center gap-2 mt-2">
                <a href="https://www.odoo.com/fr_FR/help" target="_blank" class="link-primary">Help</a>
                <a href="https://www.odoo.com/documentation/master/applications/general/iot.html" target="_blank" class="link-primary">Documentation</a>
            </div>
        </div>
    </div>
    <div t-else="" class="w-100 d-flex align-items-center justify-content-center" style="background-color: #F1F1F1; height: 100vh">
        <div class="spinner-border" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
    </div>
  `;
}
