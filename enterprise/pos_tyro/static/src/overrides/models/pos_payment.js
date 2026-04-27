import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { patch } from "@web/core/utils/patch";

patch(PosPayment.prototype, {
    setup() {
        super.setup(...arguments);
        this.tyroMerchantReceipt = null;
    },

    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        return {
            ...result,
            tyroMerchantReceipt: this.tyroMerchantReceipt,
        };
    },
});
