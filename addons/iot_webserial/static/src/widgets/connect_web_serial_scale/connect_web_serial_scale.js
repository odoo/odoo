import { Component, signal, usePlugin } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { NotificationPlugin } from "@web/core/notifications/notification_plugin";
import { WebSerialScale } from "../../web_serial_scale";

export class ConnectWebSerialScale extends Component {
    static template = `iot_webserial.ConnectWebSerialScale`;

    setup() {
        super.setup();
        this.notification = usePlugin(NotificationPlugin);
        this.loading = signal(false);
    }

    checkBrowserCompatibility() {
        if (!window.isSecureContext) {
            this.notification.add(
                _t("Connecting a scale directly requires you to access Odoo via HTTPS."),
                { type: "danger" }
            );
            return false;
        }
        if (!navigator.serial) {
            this.notification.add(
                _t(
                    "Your browser does not support connecting a scale directly. Only Chrome-based desktop browsers are supported."
                ),
                { type: "danger" }
            );
            return false;
        }
        return true;
    }

    async requestPort() {
        try {
            return await navigator.serial.requestPort();
        } catch {
            this.notification.add(_t("No device was selected."), { type: "warning" });
            return null;
        }
    }

    async openSerialScale() {
        const port = await this.requestPort();
        if (!port) {
            return;
        }

        const scale = new WebSerialScale(port);
        try {
            if (await scale.open()) {
                this.notification.add(_t("Scale connected successfully!"), { type: "success" });
                await port.close();
            } else {
                this.notification.add(_t("Your scale is not compatible with Odoo."), {
                    type: "danger",
                });
                await port.forget();
            }
        } catch {
            await port.forget();
            this.notification.add(_t("Failed to open device."), { type: "danger" });
        }
    }

    async onClick() {
        if (!this.checkBrowserCompatibility()) {
            return;
        }
        this.loading.set(true);
        await this.openSerialScale();
        this.loading.set(false);
    }
}

registry.category("view_widgets").add("iot_webserial.connect_web_serial_scale", {
    component: ConnectWebSerialScale,
});
