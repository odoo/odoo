import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { formatCurrency } from "@point_of_sale/app/models/utils/currency";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    get saleDetails() {
        let down_payment_details = [];

        // FIXME: This is a hack to handle the case where the down_payment_details is a stringified JSON.
        try {
            down_payment_details = JSON.parse(this.down_payment_details);
        } catch {
            down_payment_details = this.down_payment_details;
        }
        return down_payment_details?.map?.((detail) => ({
            product_uom_qty: detail.product_uom_qty,
            product_name: detail.product_name,
            total: formatCurrency(detail.total, this.currency),
        }));
    },
});
