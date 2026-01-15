import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { GloryService } from "@pos_glory_cash/glory";

patch(PosStore.prototype, {
    async processServerData() {
        await super.processServerData();
        for (const pm of this.models["pos.payment.method"].getAll()) {
            if (pm.payment_method_type === "glory_cash") {
                pm.payment_terminal = new GloryService(this, pm);
            }
        }
    },
});
