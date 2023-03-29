/** @odoo-module */

<<<<<<< HEAD
import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
=======
import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/pos_hook";
>>>>>>> [FIX] point_of_sale: IoT status button error fixed

// Previously ProxyStatusWidget
export class ProxyStatus extends Component {
    static template = "ProxyStatus";

    setup() {
        super.setup();
<<<<<<< HEAD
        this.pos = usePos();
        const hardwareProxy = useService("hardware_proxy");
        this.connectionInfo = useState(hardwareProxy.connectionInfo);
=======
        const initialProxyStatus = this.env.proxy.get("status");
        this.state = useState({
            status: initialProxyStatus.status,
            msg: initialProxyStatus.msg,
        });
        this.statuses = ["connected", "connecting", "disconnected", "warning"];
        this.pos = usePos();
        this.index = 0;

        onMounted(() => {
            this.env.proxy.on("change:status", this, this._onChangeStatus);
        });

        onWillUnmount(() => {
            this.env.proxy.off("change:status", this, this._onChangeStatus);
        });
>>>>>>> [FIX] point_of_sale: IoT status button error fixed
    }

    get message() {
        if (this.connectionInfo.status === "connected") {
            const { drivers } = this.connectionInfo;
            const {
                iface_scan_via_proxy,
                iface_print_via_proxy,
                iface_cashdrawer,
                iface_electronic_scale,
            } = this.env.pos.config;
            const devices = [
                {
                    name: _t("Scanner"),
                    driver: drivers.scanner,
                    enabled: iface_scan_via_proxy,
                },
                {
                    name: _t("Printer"),
                    driver: drivers.printer,
                    enabled: iface_print_via_proxy || iface_cashdrawer,
                },
                {
                    name: _t("Scale"),
                    driver: drivers.scale,
                    enabled: iface_electronic_scale,
                },
            ];
            const disconnectedDevices = devices.filter(({ enabled, driver }) => {
                return enabled && !["connected", "connecting"].includes(driver?.status);
            });
            if (disconnectedDevices.length) {
                return `${disconnectedDevices.map((d) => d.name).join(" & ")} ${_t("Offline")}`;
            }
            return "";
        }
        return this.connectionInfo.message || "";
    }
}
