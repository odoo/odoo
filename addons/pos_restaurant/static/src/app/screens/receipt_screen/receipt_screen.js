import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";

patch(ReceiptScreen.prototype, {
    continueSplitting() {
        return this.pos.continueSplitting(this.currentOrder);
    },
    isContinueSplitting() {
        return this.pos.isContinueSplitting(this.currentOrder);
    },
});
