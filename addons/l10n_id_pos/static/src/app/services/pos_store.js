import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    getQRCodeValueContext(payment) {
        return {
            ...super.getQRCodeValueContext(payment),
            qris_model: "pos.order",
            qris_model_id: payment.pos_order_id.uuid,
        };
    },
});
