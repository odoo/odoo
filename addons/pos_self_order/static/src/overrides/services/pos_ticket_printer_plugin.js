import { patch } from "@web/core/utils/patch";
import { PosTicketPrinterPlugin } from "@point_of_sale/app/plugins/pos_ticket_printer_plugin";

patch(PosTicketPrinterPlugin.prototype, {
    async printOrderReceipt({ order, printBillActionTriggered }) {
        if (
            printBillActionTriggered &&
            this.config.useDynamicQr &&
            !order.uiState.dynamicQrUrl &&
            typeof order.id === "number"
        ) {
            order.uiState.dynamicQrUrl = await this.data.call("pos.config", "get_dynamic_qr_url", [
                this.config.id,
                order.id,
            ]);
        }
        return super.printOrderReceipt(...arguments);
    },
    async printDynamicQrReceipt({ order, qrCode, webFallback = true } = {}) {
        const generator = this.getGenerator({ models: this.data.models, order });
        const data = generator.generateDynamicQrData({ qrCode });
        const iframe = await this.generateIframe("pos_self_order.DynamicQrReceipt", data);
        return await this.printWithFallback({ iframe, webFallback });
    },
});
