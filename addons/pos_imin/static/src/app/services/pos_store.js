import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";
import { IminPrinterAdapter } from "@pos_imin/app/utils/imin_printer";

const CONSOLE_COLOR = "#28ffeb";

patch(PosStore.prototype, {
    createPrinter(config) {
        if (config.printer_type === "imin") {
            try {
                const adapter = new IminPrinterAdapter({ printer: config });
                if (!adapter.isAvailable()) {
                    console.error("Imin printer is not available");
                    return false;
                }
                adapter.connect();
                return adapter;
            } catch (error) {
                logPosMessage(
                    "Store",
                    "createPrinter",
                    "Unable to create Imin printer: " + error.message,
                    CONSOLE_COLOR,
                    [error]
                );
                return false;
            }
        } else {
            return super.createPrinter(...arguments);
        }
    },
});
