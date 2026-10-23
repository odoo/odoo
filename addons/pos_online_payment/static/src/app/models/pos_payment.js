import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { patch } from "@web/core/utils/patch";

patch(PosPayment.prototype, {
    //@override
    canBeAdjusted() {
        if (this.payment_method_id.type === "online") {
            return false;
        } else {
            return super.canBeAdjusted();
        }
    },
    get isAmountEditable() {
        if (
            this.online_account_payment_id ||
            (this.payment_method_id.type === "online" && this.pos_order_id.state === "paid")
        ) {
            return false;
        }
        return super.isAmountEditable;
    },
    get isDeletable() {
        return !this.online_account_payment_id && super.isDeletable;
    },
    get currency() {
        if (this.payment_method_id.type === "online") {
            return this.config.currency_id;
        }

        return super.currency;
    },
});
