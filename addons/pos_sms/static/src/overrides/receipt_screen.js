import { patch } from "@web/core/utils/patch";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.pos.config.module_pos_sms) {
            this.state.input ||= this.currentOrder.get_partner()?.mobile || "";
        }
    },
    isValidPhoneNumber(x) {
        return x && /^\+?[()\d\s-.]{8,18}$/.test(x);
    },
});
