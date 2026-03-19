import { PosTicketPrinterService } from "@point_of_sale/app/services/pos_ticket_printer_service";
import { patch } from "@web/core/utils/patch";

patch(PosTicketPrinterService.prototype, {
    async printQrReceipt({ order, webFallback = true }) {
        const generator = this.getGenerator({ models: this.data.models, order });
        const data = generator.generateQrData();
        const iframe = await this.generateIframe("pos_self_order.pos_qr_receipt", data);
        return await this.printWithFallback({ iframe, webFallback });
    },
});
