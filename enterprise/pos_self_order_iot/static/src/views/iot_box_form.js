/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

class IoTBoxController extends formView.Controller {
    setup() {
        super.setup();
        this.notification = useService("notification");
    }

    async onWillSaveRecord(record) {
        if (!record.data.can_be_kiosk) {
            return;
        }

        const { name, ip_url, screen_orientation } = record.data;
        try {
            const rotateScreen = rpc(`${ip_url}/hw_proxy/customer_facing_display`, {
                action: "rotate_screen",
                data: screen_orientation,
            });
            this.notification.add(_t("Updating screen orientation..."), {
                title: name,
                type: "info",
            });
            await rotateScreen;

            this.notification.add(_t("Screen orientation updated."), {
                title: name,
                type: "success",
            });
        } catch {
            this.notification.add(_t("IoT is unreachable."), {
                title: name,
                type: "danger",
            });
        }
    }
}

export const iotBoxFormView = {
    ...formView,
    Controller: IoTBoxController,
};

registry.category("views").add("iot_box_form", iotBoxFormView);
