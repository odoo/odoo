import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { PaymentCashdro } from "../payment_cashdro";

patch(PosStore.prototype, {
    async processServerData() {
        await super.processServerData();
        for (const pm of this.models["pos.payment.method"].getAll()) {
            if (pm.payment_method_type === "cashdro") {
                pm.payment_terminal = new PaymentCashdro(this, pm);
            }
        }
    },
});
