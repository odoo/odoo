import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { patch } from "@web/core/utils/patch";

patch(PosPayment.prototype, {
    get currency() {
        if (this.payment_method_id.type === "online") {
            return this.config.currency_id;
        }

        return super.currency;
    },
});
