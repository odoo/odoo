import { patch } from "@web/core/utils/patch";
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
    generatePreparationData(categoryIdsSet, opts = { orderChange: null }) {
        const receipts = super.generatePreparationData(...arguments);
        for (const receipt of receipts) {
            if (["mobile", "kiosk"].includes(this.order.source)) {
                receipt.extra_data.order_name_prefix = false;
            }
        }
        return receipts;
    },
});
