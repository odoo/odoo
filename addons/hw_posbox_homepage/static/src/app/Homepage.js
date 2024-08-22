/* global owl */

import { SingleData } from "./components/SingleData.js";
import { FooterButtons } from "./components/FooterButtons.js";
import { ServerDialog } from "./components/dialog/ServerDialog.js";
import { WifiDialog } from "./components/dialog/WifiDialog.js";
import useStore from "./hooks/useStore.js";
import { UpdateDialog } from "./components/dialog/UpdateDialog.js";
import { DeviceDialog } from "./components/dialog/DeviceDialog.js";
import { SixDialog } from "./components/dialog/SixDialog.js";

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
    };

    setup() {
        this.store = useStore();
        this.state = useState({ loading: true, lastUpdate: 0 });
        this.data = useState({});
        this.store.advanced = localStorage.getItem("showAdvanced") === "true";

        onWillStart(async () => {
            await this.loadInitailData();
        });

        setInterval(() => {
            this.loadInitailData();
        }, 10000);

        setInterval(() => {
            this.state.lastUpdate = Math.round((new Date().getTime() - this.store.update) / 1000);
        }, 500);
    }

    async loadInitailData() {
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

    toggleAdvanced() {
        this.store.advanced = !this.store.advanced;
        localStorage.setItem("showAdvanced", this.store.advanced);
    }

    static template = xml`
    <div t-if="!this.state.loading" class="w-100 d-flex flex-column align-items-center justify-content-center" style="background-color: #F1F1F1; height: 100vh">
        <div class="bg-white p-4 rounded" style="min-width: 600px;">
            <div class="d-flex mb-4 flex-column align-items-center justify-content-center">
                <h4 class="text-center m-0">IoT Box - <t t-esc="this.data.hostname" /></h4>
                <div class="d-flex align-items-center justify-content-center gap-2 mt-1">
                    <span class="badge rounded-pill bg-primary cursor-pointer" t-on-click="toggleAdvanced">
                        <t t-if="this.store.advanced">Hide advanced</t>
                        <t t-else="">Show advanced</t>
                    </span>
                    <span t-att-class="this.state.lastUpdate > 30 ? 'bg-warning' : 'bg-secondary'" class="badge rounded-pill">Last update: <t t-esc="this.state.lastUpdate" /></span>
                </div>
            </div>
            <div t-if="this.store.advanced" class="alert alert-warning" role="alert">
                <p class="m-0 fw-bold">HTTPS certificate</p>
                <small>Error code: <t t-esc="this.data.certificate_details" /></small>
            </div>
            <SingleData name="'Name'" value="this.data.hostname" icon="'fa-desktop'">
				<t t-set-slot="button">
					<ServerDialog />
				</t>
			</SingleData>
            <SingleData t-if="this.store.advanced" name="'Version'" value="this.data.version" icon="'fa-microchip'">
                <t t-set-slot="button">
                    <UpdateDialog />
                </t>
            </SingleData>
            <SingleData t-if="this.store.advanced" name="'IP address'" value="this.data.ip" icon="'fa-wifi'" />
            <SingleData t-if="this.store.advanced" name="'MAC address'" value="this.data.mac.toUpperCase()" icon="'fa-id-card'" />
            <SingleData t-if="this.store.advanced" name="'Network status'" value="this.data.network_status"  icon="'fa-globe'">
                <t t-set-slot="button">
                    <WifiDialog />
                </t>
            </SingleData>
            <SingleData name="'Server status'" value="this.data.server_status" icon="'fa-server'">
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
            <SingleData name="'Devices'" value="this.data.iot_device_status.length + ' devices'" icon="'fa-tablet'">
                <t t-set-slot="button">
                    <DeviceDialog />
                </t>
            </SingleData>

            <hr class="mt-5" />
            <FooterButtons />
        </div>
    </div>
    <div t-else="" class="w-100 d-flex align-items-center justify-content-center" style="background-color: #F1F1F1; height: 100vh">
        <div class="spinner-border" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
    </div>
  `;
}
