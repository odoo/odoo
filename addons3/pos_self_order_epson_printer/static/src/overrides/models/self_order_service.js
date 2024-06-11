/** @odoo-module */

import { EpsonPrinter } from "@pos_epson_printer/app/epson_printer";
import { SelfOrder } from "@pos_self_order/app/self_order_service";
import { patch } from "@web/core/utils/patch";

patch(SelfOrder.prototype, {
    async setup() {
        await super.setup(...arguments);
        if (!this.config.epson_printer_ip || !this.config.other_devices) {
            return;
        }
        this.printer.setPrinter(
            new EpsonPrinter({
                ip: this.config.epson_printer_ip,
            })
        );
    },
    create_printer(printer) {
        if (printer.printer_type === "epson_epos") {
            return new EpsonPrinter({ ip: printer.epson_printer_ip });
        }
        return super.create_printer(...arguments);
    },
});
