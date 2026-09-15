import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { PaymentCashmatic } from "@pos_cashmatic/app/payment_cashmatic";

patch(PosStore.prototype, {
    async processServerData() {
        await super.processServerData();
        for (const pm of this.models["pos.payment.method"].getAll()) {
            if (pm.payment_method_type === "cashmatic") {
                pm.payment_terminal = new PaymentCashmatic(this, pm);
            }
        }
    },
});
