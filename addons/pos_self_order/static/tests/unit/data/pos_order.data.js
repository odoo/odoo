import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/../tests/unit/data/pos_order.data";

patch(PosOrder.prototype, {
    _should_send_to_preparation(orderId) {
        const paymentMethod = this.env["pos.payment.method"];
        const selfPaymentMethods = paymentMethod._load_pos_self_data_read(
            paymentMethod.search_read([], paymentMethod._load_pos_data_fields(), false)
        );
        return selfPaymentMethods.length === 0 || super._should_send_to_preparation(orderId);
    },
});
