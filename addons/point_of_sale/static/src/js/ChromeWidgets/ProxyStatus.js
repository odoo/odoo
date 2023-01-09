/** @odoo-module */

import PosComponent from "@point_of_sale/js/PosComponent";
import Registries from "@point_of_sale/js/Registries";

const { onMounted, onWillUnmount, useState } = owl;

// Previously ProxyStatusWidget
class ProxyStatus extends PosComponent {
    setup() {
        super.setup();
        const initialProxyStatus = this.env.proxy.get("status");
        this.state = useState({
            status: initialProxyStatus.status,
            msg: initialProxyStatus.msg,
        });
        this.statuses = ["connected", "connecting", "disconnected", "warning"];
        this.index = 0;

        onMounted(() => {
            this.env.proxy.on("change:status", this, this._onChangeStatus);
        });

        onWillUnmount(() => {
            this.env.proxy.off("change:status", this, this._onChangeStatus);
        });
    }
    _onChangeStatus(posProxy, statusChange) {
        this._setStatus(statusChange.newValue);
    }
    _setStatus(newStatus) {
        if (newStatus.status === "connected") {
            var warning = false;
            var msg = "";
            if (this.env.pos.config.iface_scan_via_proxy) {
                var scannerStatus = newStatus.drivers.scanner
                    ? newStatus.drivers.scanner.status
                    : false;
                if (scannerStatus != "connected" && scannerStatus != "connecting") {
                    warning = true;
                    msg += this.env._t("Scanner");
                }
            }
            if (this.env.pos.config.iface_print_via_proxy || this.env.pos.config.iface_cashdrawer) {
                var printerStatus = newStatus.drivers.printer
                    ? newStatus.drivers.printer.status
                    : false;
                if (printerStatus != "connected" && printerStatus != "connecting") {
                    warning = true;
                    msg = msg ? msg + " & " : msg;
                    msg += this.env._t("Printer");
                }
            }
            if (this.env.pos.config.iface_electronic_scale) {
                var scaleStatus = newStatus.drivers.scale ? newStatus.drivers.scale.status : false;
                if (scaleStatus != "connected" && scaleStatus != "connecting") {
                    warning = true;
                    msg = msg ? msg + " & " : msg;
                    msg += this.env._t("Scale");
                }
            }
            msg = msg ? msg + " " + this.env._t("Offline") : msg;

            this.state.status = warning ? "warning" : "connected";
            this.state.msg = msg;
        } else {
            this.state.status = newStatus.status;
            this.state.msg = newStatus.msg || "";
        }
    }
}
ProxyStatus.template = "ProxyStatus";

Registries.Component.add(ProxyStatus);

export default ProxyStatus;
