import { patch } from "@web/core/utils/patch";
import { PosTicketPrinterService } from "@point_of_sale/app/services/pos_ticket_printer_service";
import { SunmiPrinterAdapter } from "@pos_sunmi/app/utils/sunmi_printer";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";

const CONSOLE_COLOR = "#28ffeb";

patch(PosTicketPrinterService.prototype, {
    async createPrinterInstance(printer) {
        if (printer.printer_type === "sunmi") {
            try {
                const sunmiPrinterAdapter = new SunmiPrinterAdapter({ printer });
                await sunmiPrinterAdapter.launchPrintService();
                return sunmiPrinterAdapter;
            } catch (error) {
                console.error("Error cannot detect printer: " + error);
                logPosMessage(
                    "PosTicketPrinterService",
                    "detectSunmiPrinter",
                    "Unable to detect Sunmi printer: " + error.message,
                    CONSOLE_COLOR,
                    [error]
                );
                return null;
            }
        }
        return await super.createPrinterInstance(...arguments);
    },
});
