/* global posmodel */

import { IoTLongpolling, iotLongpollingService } from "@iot/iot_longpolling";
import { patch } from "@web/core/utils/patch";
import { iotBoxDisconnectedDialog } from "@pos_iot/app/iot_box_disconnected_dialog";

patch(iotLongpollingService, {
    dependencies: ["dialog", "hardware_proxy", ...iotLongpollingService.dependencies],
});
patch(IoTLongpolling.prototype, {
    setup({ dialog, hardware_proxy }) {
        super.setup(...arguments);
        this.hardwareProxy = hardware_proxy;
        this.dialog = dialog;
    },
    _doWarnFail(url) {
        this.dialog.add(iotBoxDisconnectedDialog, { url });
        this.hardwareProxy.setProxyConnectionStatus(url, false);
        const order = posmodel.get_order();
        if (
            order &&
            order.get_selected_paymentline() &&
            order.get_selected_paymentline().payment_method_id.use_payment_terminal ===
                "worldline" &&
            ["waiting", "waitingCard", "waitingCancel"].includes(
                order.get_selected_paymentline().payment_status
            )
        ) {
            order.get_selected_paymentline().set_payment_status("force_done");
        }
    },
    _onSuccess(iot_ip, result) {
        this.hardwareProxy.setProxyConnectionStatus(iot_ip, true);
        return super._onSuccess(...arguments);
    },
    action(iot_ip, device_identifier, data) {
        var res = super.action(...arguments);
        res.then(() => {
            this.hardwareProxy.setProxyConnectionStatus(iot_ip, true);
        }).catch(() => {
            this.hardwareProxy.setProxyConnectionStatus(iot_ip, false);
        });
        return res;
    },
});
