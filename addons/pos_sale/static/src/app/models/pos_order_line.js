import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { formatCurrency } from "@point_of_sale/app/models/utils/currency";
import { patch } from "@web/core/utils/patch";
import { parseFloat } from "@web/views/fields/parsers";
import { accountTaxHelpers } from "@account/helpers/account_tax";

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
<<<<<<< 59e583a17c7a2cbca7219e71c4275d7753128de9
||||||| 0f577f1d3a9bf80991b043695bfde9510593e301
    /**
     * Set quantity based on the give sale order line.
     * @param {'sale.order.line'} saleOrderLine
     */
    async setQuantityFromSOL(saleOrderLine) {
        if (
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
=======
    /**
     * Set quantity based on the give sale order line.
     * @param {'sale.order.line'} saleOrderLine
     */
    async setQuantityFromSOL(saleOrderLine) {
        if (
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
    setUnitPrice(price) {
        if (!this.sale_order_line_id) {
            return super.setUnitPrice(price);
        }
        // Keep the full unit price of the sale order line, as the sale order doesn't round it
        this.price_unit = (isNaN(price) ? parseFloat("" + price) : Number(price)) || 0;
    },
>>>>>>> 9aba95aa11ffe1682ded4d5b8512560aa29ec35e
    getBaseLine(opts = {}) {
        const extraTaxData = this.extra_tax_data;
        const quantity = "quantity" in opts ? opts.quantity : this.getQuantity();
        const storedQty = extraTaxData?.quantity;
        const signFlipped = storedQty && quantity && Math.sign(storedQty) !== Math.sign(quantity);
        if (signFlipped) {
            return super.getBaseLine({
                ...opts,
                extra_tax_data:
                    accountTaxHelpers.reverse_quantity_base_line_extra_tax_data(extraTaxData),
            });
        }
        return super.getBaseLine(opts);
    },
});
