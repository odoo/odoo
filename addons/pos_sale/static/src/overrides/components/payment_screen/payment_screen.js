/** @odoo-module **/

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    async afterOrderValidation() {
        const lines = this.currentOrder.lines.filter(
            (e) => e.sale_order_origin_id && e.down_payment_details
        );
        if (lines.length > 0) {
            const orders = [...new Set(lines.map((e) => e.sale_order_origin_id))];
            await this.pos.data.read(
                "sale.order.line",
                orders.flatMap((o) => o.order_line).map((ol) => ol.id)
            );
            this.pos.data.syncDataWithIndexedDB(this.pos.data.records);
        }
        await super.afterOrderValidation();
    },
});
