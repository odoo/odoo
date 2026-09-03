import { patch } from "@web/core/utils/patch";
import { GeneratePrinterData } from "@point_of_sale/app/utils/printer/generate_printer_data";

/**
 * This class is a JS copy of the class PosOrderReceipt in Python.
 */
patch(GeneratePrinterData.prototype, {
    generateReceiptData() {
        const data = super.generateReceiptData(...arguments);
        if (this.order.payment_ids.some((p) => p.payment_provider === "bancontact_pay")) {
            data.extra_data["processed_by_bancontact"] = true;
            data.image["bancontact_logo"] = "/pos_bancontact_pay/static/img/receipt/logo.svg";
        }
        return data;
    },
});
