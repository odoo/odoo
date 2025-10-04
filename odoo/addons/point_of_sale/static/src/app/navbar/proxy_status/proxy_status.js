/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

// Previously ProxyStatusWidget
export class ProxyStatus extends Component {
    static template = "point_of_sale.ProxyStatus";

    setup() {
        this.pos = usePos();
        this.ui = useState(useService("ui"));
        const hardwareProxy = useService("hardware_proxy");
        this.connectionInfo = useState(hardwareProxy.connectionInfo);
    }

    get message() {
        if (this.connectionInfo.status === "connected") {
            const { drivers } = this.connectionInfo;
            const {
                iface_scan_via_proxy,
                iface_print_via_proxy,
                iface_cashdrawer,
                iface_electronic_scale,
            } = this.pos.config;
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
