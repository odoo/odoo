/* global owl */

import { SingleData } from "./components/single_data.js";
import { FooterButtons } from "./components/footer_buttons.js";
import { DatabaseDialog } from "./components/dialog/database_dialog.js";
import { WifiDialog } from "./components/dialog/wifi_dialog.js";
import useStore from "./hooks/store_hook.js";
import { UpdateDialog } from "./components/dialog/update_dialog.js";
import { DeviceDialog } from "./components/dialog/device_dialog.js";
import { SixTerminalDialog } from "./components/dialog/six_terminal_dialog.js";
import { LoadingFullScreen } from "./components/loading_full_screen.js";
import { IconButton } from "./components/icon_button.js";

const { Component, xml, onWillStart, signal, computed } = owl;

export class Homepage extends Component {
    static components = {
        SingleData,
        FooterButtons,
        DatabaseDialog,
        WifiDialog,
        UpdateDialog,
        DeviceDialog,
        SixTerminalDialog,
        LoadingFullScreen,
        IconButton,
    };

    store = useStore();

    loading = signal(true);
    waitRestart = signal(false);

    loadDataDelay = 10000;

    numDevices = computed(() =>
        Object.values(this.store.base().devices)
            .map((devices) => devices.length)
            .reduce((a, b) => a + b, 0)
    );
    networkStatus = computed(() => {
        if (
            !this.store.isLinux() ||
            this.store.base().network_interfaces.some((netInterface) => !netInterface.is_wifi)
        ) {
            return "Ethernet";
        }
        const wifiInterface = this.store
            .base()
            .network_interfaces.find((netInterface) => netInterface.ssid);
        if (wifiInterface) {
            return this.store.base().is_access_point_up
                ? 'No internet connection - click on "Configure"'
                : `Wi-Fi: ${wifiInterface.ssid}`;
        }
        return "Not Connected";
    });

    setup() {
        this.store.advanced.set(localStorage.getItem("showAdvanced") === "true");
        onWillStart(async () => {
            await this.loadInitialData();
        });
    }

    async loadInitialData() {
        try {
            const data = await this.store.rpc({
                url: "/iot_drivers/data",
            });

            if (data.system === "Linux") {
                this.store.isLinux.set(true);
            }

            this.store.base.set(data);
            this.loading.set(false);
            this.store.update.set(new Date().getTime());
        } catch {
            console.warn("Error while fetching data");
        }
        this.loadDataDelay *= 1.25;
        setTimeout(async () => {
            await this.loadInitialData();
        }, Math.min(this.loadDataDelay, 30 * 60 * 1000));
    }

    async restartOdooService() {
        try {
            await this.store.rpc({
                url: "/iot_drivers/restart_odoo_service",
            });

            this.waitRestart.set(true);
        } catch {
            console.warn("Error while restarting Odoo Service");
        }
    }

    toggleAdvanced() {
        this.store.advanced.set(!this.store.advanced());
        localStorage.setItem("showAdvanced", this.store.advanced());
    }

    static template = xml`
    <t t-translation="off">
        <LoadingFullScreen t-if="this.waitRestart()">
            <t t-set-slot="body">
            Restarting IoT Box, please wait...
            </t>
        </LoadingFullScreen>

        <div t-if="!this.loading()" class="w-100 d-flex flex-column align-items-center justify-content-center background">
            <div class="bg-white p-4 rounded overflow-auto position-relative w-100 main-container">
                <div class="position-absolute end-0 top-0 mt-3 me-4 d-flex gap-1">
                    <IconButton t-if="!this.store.base().is_access_point_up" onClick.bind="this.toggleAdvanced" icon="this.store.advanced() ? 'fa-cog' : 'fa-cogs'" />
                    <IconButton onClick.bind="this.restartOdooService" icon="'fa-power-off'" />
                </div>
                <div class="d-flex mb-4 flex-column align-items-center justify-content-center">
                    <h4 class="text-center m-0">IoT Box</h4>
                </div>
                <div t-if="!this.store.base().certificate_end_date and !this.store.base().is_access_point_up" class="alert alert-warning" role="alert">
                    <p class="m-0 fw-bold">
                        This IoT Box doesn't have a valid certificate.
                    </p>
                    <small>
                        The IoT Box should get a certificate automatically when paired with a database. If it doesn't, 
                        try to restart it.
                    </small>
                </div>
                <div t-if="this.store.advanced() and this.store.base().certificate_end_date and !this.store.base().is_access_point_up" class="alert alert-info" role="alert">
                    Your IoT Box subscription is valid until <span class="fw-bold" t-out="this.store.base().certificate_end_date"/>.
                </div>
                <div t-if="this.store.base().is_access_point_up" class="alert alert-info" role="alert">
                    <p class="m-0 fw-bold">No Internet Connection</p>
                    <small>
                        Please connect your IoT Box to internet via an ethernet cable or via Wi-Fi by clicking on "Configure" below
                    </small>
                </div>
                <SingleData name="'Identifier'" value="this.store.base().identifier" icon="'fa-address-card'" />
                <SingleData t-if="this.store.advanced()" name="'Mac Address'" value="this.store.base().mac_address" icon="'fa-address-book'" />
                <SingleData t-if="this.store.advanced()" name="'Version'" value="this.store.base().version" icon="'fa-microchip'">
                    <t t-set-slot="button">
                        <UpdateDialog />
                    </t>
                </SingleData>
                <SingleData t-if="this.store.advanced()" name="'IP address'" value="this.store.base().ip" icon="'fa-globe'" />
                <SingleData t-if="this.store.isLinux()" name="'Internet Status'" value="this.networkStatus()" icon="'fa-wifi'">
                    <t t-set-slot="button">
                        <WifiDialog />
                    </t>
                </SingleData>
                <SingleData t-if="!this.store.base().is_access_point_up" name="'Odoo database connected'" value="this.store.base().server_status" icon="'fa-link'">
                    <t t-set-slot="button">
                        <DatabaseDialog />
                    </t>
                </SingleData>
                <SingleData t-if="this.store.base().pairing_code and !this.store.base().is_access_point_up and !this.store.base().pairing_code_expired" name="'Pairing Code'" value="this.store.base().pairing_code + ' - Enter this code in the IoT app in your Odoo database'" icon="'fa-code'"/>
                <SingleData t-if="this.store.base().pairing_code_expired" name="'Pairing Code'" value="'Code has expired - restart the IoT Box to generate a new one'" icon="'fa-code'"/>
                <SingleData  t-if="this.store.advanced() and !this.store.base().is_access_point_up" name="'Six terminal'" value="this.store.base().six_terminal" icon="'fa-money'">
                    <t t-set-slot="button">
                        <SixTerminalDialog />
                    </t>
                </SingleData>
                <SingleData t-if="!this.store.base().is_access_point_up" name="'Devices'" value="this.numDevices() + ' devices'" icon="'fa-plug'">
                    <t t-set-slot="button">
                        <DeviceDialog />
                    </t>
                </SingleData>

                <hr class="mt-5" />
                <FooterButtons />
                <div class="d-flex justify-content-center gap-2 mt-2" t-if="!this.store.base().is_access_point_up">
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
