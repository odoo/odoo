import { patch } from "@web/core/utils/patch";
import { PosTicketPrinterService } from "@point_of_sale/app/services/pos_ticket_printer_service";

patch(PosTicketPrinterService.prototype, {
    showPrinterErrorDialog(message, retryFunction, fallbackFunction = undefined) {
        return false;
    },
    async markReceiptAsPrinted(order) {
        return false;
    },
});
