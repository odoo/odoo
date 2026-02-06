import { patch } from "@web/core/utils/patch";
import { PosTicketPrinterService } from "@point_of_sale/app/services/pos_ticket_printer_service";

patch(PosTicketPrinterService.prototype, {
    async printOrderReceipt({
        order,
        basic = false,
        printBillActionTriggered = false,
        webFallback = true,
    } = {}) {
        const isOffline = this.data.network.offline;

        if (!isOffline && order?.isPrintEcpayInvoice && !order.ecpay_error) {
            await this.env.services.pos._getUniformInvoiceData(order, { throw: true });
        }
        const result = await super.printOrderReceipt({ order });
        if (result && !isOffline && order?.isPrintEcpayInvoice && !order.ecpay_error) {
            const data = this.getOrderReceiptData(order, basic);
            const ecpay_certificate_receipt_iframe = await this.generateIframe(
                "l10n_tw_edi_ecpay_pos.ecpay_certificate_receipt",
                data
            );
            await this.printWithFallback({ iframe: ecpay_certificate_receipt_iframe, webFallback });
            const ecpay_transaction_receipt_iframe = await this.generateIframe(
                "l10n_tw_edi_ecpay_pos.ecpay_transaction_receipt",
                data
            );
            await this.printWithFallback({ iframe: ecpay_transaction_receipt_iframe, webFallback });
        }
        return result;
    },
});
