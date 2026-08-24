import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { formatCurrency } from "@point_of_sale/app/models/utils/currency";
import { patch } from "@web/core/utils/patch";
import { accountTaxHelpers } from "@account/helpers/account_tax";

patch(PosOrderline.prototype, {
    /**
     * Tax mode inherited from the originating sale order (when the line results from settling a
     * sale order). This is consumed by the taxes computation so the POS interprets the unit price
     * as tax included/excluded consistently with the sale order, regardless of the tax's own
     * price_include configuration. Returns null for regular POS lines.
     */
    get documentTaxMode() {
        return this.sale_order_origin_id?.document_tax_mode || super.documentTaxMode;
    },

    get orderDisplayProductName() {
        if (this.config.default_product_id.id === this.product_id.id) {
            return {
                name: this.sale_order_line_id.name,
                attributeString: "",
            };
        }
        return super.orderDisplayProductName;
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
