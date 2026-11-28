import { patch } from "@web/core/utils/patch";
import { PosTicketPrinterPlugin } from "@point_of_sale/app/plugins/pos_ticket_printer_plugin";
import { waitImages } from "@point_of_sale/utils";

patch(PosTicketPrinterPlugin.prototype, {
    printWeb(iframe) {
        if (this.ecpayWebIframes) {
            this.ecpayWebIframes.push(iframe);
            return;
        }
        return super.printWeb(...arguments);
    },

    async printOrderReceipt({
        order,
        basic = false,
        printBillActionTriggered = false,
        webFallback = true,
    } = {}) {
        const isOffline = this.data.network.offline;

        if (
            !printBillActionTriggered &&
            !isOffline &&
            order?.isPrintEcpayInvoice &&
            !order.ecpay_error
        ) {
            await this.env.services.pos._getUniformInvoiceData(order, { throw: true });
        }
        const printEcpay =
            !printBillActionTriggered &&
            !isOffline &&
            order?.isPrintEcpayInvoice &&
            !order.ecpay_error;
        this.ecpayWebIframes = printEcpay ? [] : null;
        let result, webIframes;
        try {
            result = await super.printOrderReceipt(...arguments);
            if (printEcpay) {
                const data = this.getOrderReceiptData(order, basic);
                const ecpay_certificate_receipt_iframe = await this.generateIframe(
                    "l10n_tw_edi_ecpay_pos.ecpay_certificate_receipt",
                    data
                );
                await this.printWithFallback({
                    iframe: ecpay_certificate_receipt_iframe,
                    webFallback,
                });
                const ecpay_transaction_receipt_iframe = await this.generateIframe(
                    "l10n_tw_edi_ecpay_pos.ecpay_transaction_receipt",
                    data
                );
                await this.printWithFallback({
                    iframe: ecpay_transaction_receipt_iframe,
                    webFallback,
                });
            }
        } finally {
            webIframes = this.ecpayWebIframes;
            this.ecpayWebIframes = null;
        }
        if (webIframes?.length) {
            // The last generated iframe is the only one still displayed
            const iframe = webIframes.at(-1);
            iframe.srcdoc = webIframes
                .map((webIframe) => webIframe.srcdoc)
                .join('<div style="page-break-after: always;"></div>');
            await new Promise((resolve) => (iframe.onload = resolve));
            await waitImages(iframe.contentDocument.body);
            this.printWeb(iframe);
        }
        return result;
    },
});
