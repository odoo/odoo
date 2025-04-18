import { DeviceController } from "@iot_base/device_controller";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

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

export function useSingleDialog() {
    let close = null;
    const dialog = useService("dialog");
    return {
        open(dialogClass, props) {
            // If the dialog is already open, we don't want to open a new one
            if (!close) {
                close = dialog.add(dialogClass, props, {
                    onClose: () => {
                        close = null;
                    },
                });
            }
        },
        close() {
            close?.();
        },
    };
}
