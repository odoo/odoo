import { patch } from "@web/core/utils/patch";
import { PosTicketPrinterPlugin } from "@point_of_sale/app/plugins/pos_ticket_printer_plugin";

patch(PosTicketPrinterPlugin.prototype, {
    showPrinterErrorDialog(message, retryFunction, fallbackFunction = undefined) {
        return false;
    },
    async markReceiptAsPrinted(order) {
        return false;
    },
});
