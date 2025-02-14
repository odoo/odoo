import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    export_for_printing(baseUrl, headerData) {
        const result = super.export_for_printing(...arguments);
        const tyroMerchantReceiptPaymentLine = result.paymentlines.find(
            (line) => line.tyroMerchantReceipt
        );
        if (tyroMerchantReceiptPaymentLine) {
            result.paymentlines = [
                {
                    ...tyroMerchantReceiptPaymentLine,
                    ticket: tyroMerchantReceiptPaymentLine.tyroMerchantReceipt,
                },
            ];
        }
        return result;
    },
});
