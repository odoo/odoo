import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";
import { SunmiPrinterAdapter } from "@pos_sunmi/app/utils/sunmi_printer";

const CONSOLE_COLOR = "#28ffeb";

patch(PosStore.prototype, {
    async afterProcessServerData() {
        const result = await super.afterProcessServerData(...arguments);
        if (this.config.other_devices) {
            // Check if the Sunmi printer is available; if not, fallback to the existing printer
            this.detectSunmiPrinter();
        }
        return result;
    },
    async detectSunmiPrinter() {
        try {
            const sunmiPrinterAdapter = new SunmiPrinterAdapter({
                fallbackPrinter: this.hardwareProxy.printer,
            });
            const isAvailable = await sunmiPrinterAdapter.isAvailable();
            if (isAvailable) {
                this.sunmiPrinterAdapter = sunmiPrinterAdapter; // Store the adapter for later use
                this.hardwareProxy.printer = this.sunmiPrinterAdapter;
                await this.sunmiPrinterAdapter.connect();
            }
        } catch (error) {
            logPosMessage(
                "Store",
                "detectSunmiPrinter",
                "Unable to detect Sunmi printer: " + error.message,
                CONSOLE_COLOR,
                [error]
            );
        }
    },
});
