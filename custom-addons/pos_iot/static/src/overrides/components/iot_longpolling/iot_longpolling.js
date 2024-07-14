/** @odoo-module */
/* global posmodel */

import { _t } from "@web/core/l10n/translation";
import { IoTLongpolling, iotLongpollingService } from "@iot/iot_longpolling";
import { patch } from "@web/core/utils/patch";
import { IoTErrorPopup } from "@pos_iot/app/io_t_error_popup/io_t_error_popup";

patch(iotLongpollingService, {
    dependencies: ["popup", "hardware_proxy", ...iotLongpollingService.dependencies],
});
patch(IoTLongpolling.prototype, {
    setup({ popup, hardware_proxy }) {
        super.setup(...arguments);
        this.popup = popup;
        this.hardwareProxy = hardware_proxy;
    },
    _doWarnFail(url) {
        this.popup.add(IoTErrorPopup, {
            title: _t("Connection to IoT Box failed"),
            url: url,
        });
        this.hardwareProxy.setProxyConnectionStatus(url, false);
        const order = posmodel.get_order();
        if (
            order &&
            order.selected_paymentline &&
            order.selected_paymentline.payment_method.use_payment_terminal === "worldline" &&
            ["waiting", "waitingCard", "waitingCancel"].includes(
                order.selected_paymentline.payment_status
            )
        ) {
            order.selected_paymentline.set_payment_status("force_done");
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
