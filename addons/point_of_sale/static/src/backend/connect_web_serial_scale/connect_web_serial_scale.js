import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { WebSerialScale } from "@point_of_sale/app/utils/scale/web_serial_scale";

export class ConnectWebSerialScale extends Component {
    static template = `point_of_sale.ConnectWebSerialScale`;
    static props = {
        ...standardWidgetProps,
    };

    setup() {
        super.setup();
        this.notification = useService("notification");
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

    async openSerialScale() {
        try {
            const port = await navigator.serial.requestPort();
            const scale = new WebSerialScale(this, port);
            if (await scale.isScaleSupported()) {
                this.notification.add(
                    _t("Scale connected successfully! It will be used automatically in the POS."),
                    { type: "success" }
                );
                await port.close();
            } else {
                this.notification.add(_t("Your scale is not compatible with Odoo."), {
                    type: "danger",
                });
            }
        } catch {
            this.notification.add(_t("No device was selected."), { type: "warning" });
        }
    }

    async onClick() {
        if (!this.checkBrowserCompatibility()) {
            return;
        }
        await this.openSerialScale();
    }
}

export const connectWebSerialScaleWidget = {
    component: ConnectWebSerialScale,
};
registry
    .category("view_widgets")
    .add("point_of_sale_connect_web_serial_scale", connectWebSerialScaleWidget);
