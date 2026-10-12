import { patch } from "@web/core/utils/patch";
import { IminPrinterAdapter } from "../utils/imin_printer";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";
import { PosTicketPrinterPlugin } from "@point_of_sale/app/plugins/pos_ticket_printer_plugin";

const CONSOLE_COLOR = "#28ffeb";

patch(PosTicketPrinterPlugin.prototype, {
    async createPrinterInstance(printer) {
        if (printer.printer_type === "imin") {
            try {
                const iminPrinterAdapter = new IminPrinterAdapter({ printer });
                const isAvailable = await iminPrinterAdapter.isAvailable();
                if (!isAvailable) {
                    return false;
                }

                printer._instance = iminPrinterAdapter;
                await iminPrinterAdapter.connect();
                return iminPrinterAdapter;
            } catch (error) {
                logPosMessage(
                    "PosTicketPrinterService",
                    "detectIminPrinter",
                    "Unable to detect Imin printer: " + error.message,
                    CONSOLE_COLOR,
                    [error]
                );
            }
        }

        return await super.createPrinterInstance(...arguments);
    },
});
