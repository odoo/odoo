import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { formatCurrency } from "@point_of_sale/app/models/utils/currency";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    setup(_defaultObj) {
        super.setup(...arguments);
        // It is possible that this orderline is initialized using server data,
        // meaning, it is loaded from localStorage or from server. This means
        // that some fields has already been assigned. Therefore, we only set the options
        // when the original value is falsy.
        if (this.sale_order_origin_id?.shipping_date) {
            this.order_id.setShippingDate(this.sale_order_origin_id.shipping_date);
        }
    },
    getSaleOrder() {
        if (this.sale_order_origin_id) {
            const value = {
                name: this.sale_order_origin_id.name,
                details: this.down_payment_details || false,
            };

            return value;
        }
        return false;
    },
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
    /**
     * Set quantity based on the give sale order line.
     * @param {'sale.order.line'} saleOrderLine
     */
    async setQuantityFromSOL(saleOrderLine) {
        if (!saleOrderLine.has_valued_move_ids && !saleOrderLine.is_downpayment) {
            this.setQuantity(saleOrderLine.product_uom_qty);
        } else if (
            this.product_id.type === "service" &&
            !["sent", "draft"].includes(this.sale_order_origin_id.state)
        ) {
            this.setQuantity(saleOrderLine.qty_to_invoice);
        } else {
            this.setQuantity(
                saleOrderLine.product_uom_qty -
                    Math.max(saleOrderLine.qty_delivered, saleOrderLine.qty_invoiced)
            );
        }
    },
});
