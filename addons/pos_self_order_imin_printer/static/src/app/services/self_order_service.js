import { patch } from "@web/core/utils/patch";
import { SelfOrder } from "@pos_self_order/app/services/self_order_service";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";
import { IminPrinterAdapter } from "@pos_imin/app/utils/imin_printer";

const CONSOLE_COLOR = "#28ffeb";

patch(SelfOrder.prototype, {
    async setup() {
        await super.setup(...arguments);

        if (this.config.other_devices) {
            this.detectIminPrinter();
        }
    },

    async detectIminPrinter() {
        try {
            const iminPrinterAdapter = new IminPrinterAdapter({
                fallbackPrinter: this.printer.device,
            });
            const isAvailable = await iminPrinterAdapter.isAvailable();
            if (isAvailable) {
                this.iminPrinterAdapter = iminPrinterAdapter; // Store the adapter for later use
                this.printer.setPrinter(this.iminPrinterAdapter);
                await this.iminPrinterAdapter.connect();
            }
        } catch (error) {
            logPosMessage(
                "Store",
                "detectIminPrinter",
                "Unable to detect Imin printer: " + error.message,
                CONSOLE_COLOR,
                [error]
            );
        }
    },
});
