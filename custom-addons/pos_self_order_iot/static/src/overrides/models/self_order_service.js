/** @odoo-module */

import { IoTPrinter } from "@pos_iot/app/iot_printer";
import { DeviceController } from "@iot/device_controller";
import { SelfOrder, selfOrderService } from "@pos_self_order/app/self_order_service";
import { patch } from "@web/core/utils/patch";

patch(selfOrderService, {
    dependencies: [...selfOrderService.dependencies, "iot_longpolling"],
});

patch(SelfOrder.prototype, {
    async setup(env, services) {
        this.iot_longpolling = services.iot_longpolling;
        await super.setup(...arguments);
    },
    create_printer(printer) {
        if (printer.device_identifier && printer.printer_type === "iot") {
            const device = new DeviceController(this.iot_longpolling, {
                iot_ip: printer.proxy_ip,
                identifier: printer.device_identifier,
            });
            return new IoTPrinter({ device });
        } else {
            return super.create_printer(...arguments);
        }
    },
});
