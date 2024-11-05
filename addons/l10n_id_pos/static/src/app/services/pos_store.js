import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";
import { user } from "@web/core/user";

patch(PosStore.prototype, {
    async showQR(payment) {
        // Add context to signal backend it's coming from PoS
        user.updateContext({ qris_model: "pos.order", qris_model_id: payment.pos_order_id.uuid });
        return await super.showQR(payment);
    },
});
