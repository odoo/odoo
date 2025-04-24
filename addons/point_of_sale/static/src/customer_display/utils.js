import { DeviceController } from "@iot_base/device_controller";
import { _t } from "@web/core/l10n/translation";

export function openProxyCustomerDisplay(displayDeviceIp, pos, notificationService = null) {
    if (!displayDeviceIp) {
        return;
    }

    pos.hardwareProxy.deviceControllers.customerDisplay ??= new DeviceController(
        pos.iotLongpolling,
        { iot_ip: displayDeviceIp, identifier: "display" }
    );

    notificationService?.add(_t("Connecting to the IoT Box"));
    pos.hardwareProxy.deviceControllers.customerDisplay.action({
        action: "open",
        access_token: pos.config.access_token,
        pos_id: pos.config.id,
    });
}
