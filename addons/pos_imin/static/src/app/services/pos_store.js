import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";
import { IminPrinterAdapter } from "@pos_imin/app/utils/imin_printer";

const CONSOLE_COLOR = "#28ffeb";

patch(PosStore.prototype, {
    async afterProcessServerData() {
        const result = await super.afterProcessServerData(...arguments);
        if (this.config.other_devices) {
            // Check if the Imin printer is available; if not, fallback to the existing printer
            this.detectIminPrinter();
        }
        return result;
    },
    async detectIminPrinter() {
        try {
            const iminPrinterAdapter = new IminPrinterAdapter({
                fallbackPrinter: this.hardwareProxy.printer,
            });
            const isAvailable = await iminPrinterAdapter.isAvailable();
            if (isAvailable) {
                this.iminPrinterAdapter = iminPrinterAdapter; // Store the adapter for later use
                this.hardwareProxy.printer = this.iminPrinterAdapter;
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
