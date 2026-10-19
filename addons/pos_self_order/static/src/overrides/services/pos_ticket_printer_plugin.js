import { patch } from "@web/core/utils/patch";
import { PosTicketPrinterPlugin } from "@point_of_sale/app/plugins/pos_ticket_printer_plugin";

patch(PosTicketPrinterPlugin.prototype, {
    async printDynamicQrReceipt({ order, qrCode, webFallback = true } = {}) {
        const generator = this.getGenerator({ models: this.data.models, order });
        const data = generator.generateDynamicQrData({ qrCode });
        const iframe = await this.generateIframe("pos_self_order.DynamicQrReceipt", data);
        return await this.printWithFallback({ iframe, webFallback });
    },
});
