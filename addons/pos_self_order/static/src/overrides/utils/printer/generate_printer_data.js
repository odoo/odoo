import { patch } from "@web/core/utils/patch";
import { qrCodeSrc } from "@point_of_sale/utils";
import { GeneratePrinterData } from "@point_of_sale/app/utils/printer/generate_printer_data";

/**
 * This class is a JS copy of the class PosOrderReceipt in Python.
 */
patch(GeneratePrinterData.prototype, {
    generateReceiptData() {
        const data = super.generateReceiptData(...arguments);
        data.conditions.from_self = ["mobile", "kiosk"].includes(this.order.source);
        return data;
    },
    /**
     * Methods bellow are used to generate qr tickets data
     */
    generateQrData() {
        const { self_ordering_url } = this.config;
        console.log(`${self_ordering_url}&order_uuid=${this.order.uuid}`);
        return {
            company: this.company.raw,
            order: this.order.raw,
            config: this.config.raw,
            image: {
                logo: this.config.receiptLogoUrl,
                qrCode: qrCodeSrc(`${self_ordering_url}&order_uuid=${this.order.uuid}`, {
                    size: 240,
                }),
            },
            extra_data: {
                ...this.commonExtraData,
                date: new Date().toLocaleString(),
                table: this.order.table_id ? this.order.table_id.table_number : null,
            },
        };
    },
});
