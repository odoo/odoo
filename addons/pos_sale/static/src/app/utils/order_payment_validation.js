import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { patch } from "@web/core/utils/patch";

patch(OrderPaymentValidation.prototype, {
    async afterOrderValidation() {
        const lines = this.order.lines.filter(
            (e) => e.sale_order_origin_id && e.down_payment_details
        );
        if (lines.length > 0) {
            const orders = [...new Set(lines.map((e) => e.sale_order_origin_id))];
            await this.pos.data.read(
                "sale.order.line",
                orders.flatMap((o) => o.order_line).map((ol) => ol.id)
            );
        }
        await super.afterOrderValidation();
    },
});
