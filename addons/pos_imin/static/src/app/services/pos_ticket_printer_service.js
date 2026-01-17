import { patch } from "@web/core/utils/patch";
import { PosTicketPrinterService } from "@point_of_sale/app/services/pos_ticket_printer_service";
import { IminPrinterAdapter } from "../utils/imin_printer";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";

const CONSOLE_COLOR = "#28ffeb";

patch(PosTicketPrinterService.prototype, {
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
