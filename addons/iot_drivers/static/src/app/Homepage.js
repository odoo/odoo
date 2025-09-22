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
        this.state = useState({ data: {}, loading: true, waitRestart: false });
        this.store.advanced = localStorage.getItem("showAdvanced") === "true";
        this.store.dev = new URLSearchParams(window.location.search).has("debug");

        onWillStart(async () => {
            await this.loadInitialData();
        });

        setInterval(() => {
            this.loadInitialData();
        }, 10000);
    }

    get numDevices() {
        return Object.values(this.state.data.devices)
            .map((devices) => devices.length)
            .reduce((a, b) => a + b, 0);
    }

    get networkStatus() {
        if (
            !this.store.isLinux ||
            this.state.data.network_interfaces.some((netInterface) => !netInterface.is_wifi)
        ) {
            return "Ethernet";
        }
        const wifiInterface = this.state.data.network_interfaces.find(
            (netInterface) => netInterface.ssid
        );
        if (wifiInterface) {
            return this.state.data.is_access_point_up
                ? 'No internet connection - click on "Configure"'
                : `Wi-Fi: ${wifiInterface.ssid}`;
        }
        return "Not Connected";
    }

    async loadInitialData() {
        try {
            const data = await this.store.rpc({
                url: "/iot_drivers/data",
            });

            if (data.system === "Linux") {
                this.store.isLinux = true;
            }

            this.state.data = data;
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
                url: "/iot_drivers/restart_odoo_service",
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
    <t t-translation="off">
        <LoadingFullScreen t-if="this.state.waitRestart">
            <t t-set-slot="body">
            Restarting IoT Box, please wait...
            </t>
        </LoadingFullScreen>

        <div t-if="!this.state.loading" class="w-100 d-flex flex-column align-items-center justify-content-center background">
            <div class="bg-white p-4 rounded overflow-auto position-relative w-100 main-container">
                <div class="position-absolute end-0 top-0 mt-3 me-4 d-flex gap-1">
                    <IconButton t-if="!store.base.is_access_point_up" onClick.bind="toggleAdvanced" icon="this.store.advanced ? 'fa-cog' : 'fa-cogs'" />
                    <IconButton onClick.bind="restartOdooService" icon="'fa-power-off'" />
                </div>
                <div class="d-flex mb-4 flex-column align-items-center justify-content-center">
                    <h4 class="text-center m-0">IoT Box</h4>
                </div>
                <div t-if="!state.data.certificate_end_date and !store.base.is_access_point_up" class="alert alert-warning" role="alert">
                    <p class="m-0 fw-bold">
                        This IoT Box doesn't have a valid certificate.
                    </p>
                    <small>
                        The IoT Box should get a certificate automatically when paired with a database. If it doesn't, 
                        try to restart it.
                    </small>
                </div>
                <div t-if="store.advanced and state.data.certificate_end_date and !store.base.is_access_point_up" class="alert alert-info" role="alert">
                    Your IoT Box subscription is valid until <span class="fw-bold" t-esc="state.data.certificate_end_date"/>.
                </div>
                <div t-if="store.base.is_access_point_up" class="alert alert-info" role="alert">
                    <p class="m-0 fw-bold">No Internet Connection</p>
                    <small>
                        Please connect your IoT Box to internet via an ethernet cable or via Wi-Fi by clicking on "Configure" below
                    </small>
                </div>
                <SingleData name="'Identifier'" value="state.data.identifier" icon="'fa-address-card'" />
                <SingleData t-if="store.advanced" name="'Mac Address'" value="state.data.mac_address" icon="'fa-address-book'" />
                <SingleData t-if="store.advanced" name="'Version'" value="state.data.version" icon="'fa-microchip'">
                    <t t-set-slot="button">
                        <UpdateDialog />
                    </t>
                </SingleData>
                <SingleData t-if="store.advanced" name="'IP address'" value="state.data.ip" icon="'fa-globe'" />
                <SingleData t-if="store.isLinux" name="'Internet Status'" value="networkStatus" icon="'fa-wifi'">
                    <t t-set-slot="button">
                        <WifiDialog />
                    </t>
                </SingleData>
                <SingleData t-if="!store.base.is_access_point_up" name="'Odoo database connected'" value="state.data.server_status" icon="'fa-link'">
                    <t t-set-slot="button">
                        <ServerDialog />
                    </t>
                </SingleData>
                <SingleData t-if="state.data.pairing_code and !this.store.base.is_access_point_up and !state.data.pairing_code_expired" name="'Pairing Code'" value="state.data.pairing_code + ' - Enter this code in the IoT app in your Odoo database'" icon="'fa-code'"/>
                <SingleData t-if="state.data.pairing_code_expired" name="'Pairing Code'" value="'Code has expired - restart the IoT Box to generate a new one'" icon="'fa-code'"/>
                <SingleData  t-if="store.advanced and !store.base.is_access_point_up" name="'Six terminal'" value="state.data.six_terminal" icon="'fa-money'">
                    <t t-set-slot="button">
                        <SixDialog />
                    </t>
                </SingleData>
                <SingleData t-if="!this.store.base.is_access_point_up" name="'Devices'" value="numDevices + ' devices'" icon="'fa-plug'">
                    <t t-set-slot="button">
                        <DeviceDialog />
                    </t>
                </SingleData>

                <hr class="mt-5" />
                <FooterButtons />
                <div class="d-flex justify-content-center gap-2 mt-2" t-if="!store.base.is_access_point_up">
                    <a href="https://www.odoo.com/fr_FR/help" target="_blank" class="link-primary">Help</a>
                    <a href="https://www.odoo.com/documentation/latest/applications/general/iot.html" target="_blank" class="link-primary">Documentation</a>
                </div>
            </div>
        </div>
        <div t-else="" class="w-100 d-flex align-items-center justify-content-center background">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>
    </t>
  `;
}
