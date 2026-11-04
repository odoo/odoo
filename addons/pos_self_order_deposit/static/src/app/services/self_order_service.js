import { patch } from "@web/core/utils/patch";
import { SelfOrder } from "@pos_self_order/app/services/self_order_service";
import { getOrderLineValues } from "@pos_self_order/app/services/card_utils";

patch(SelfOrder.prototype, {
    async addToCart() {
        const result = await super.addToCart(...arguments);
        this.addMissingDepositLines();
        return result;
    },

    addMissingDepositLines() {
        if (!this.config.module_pos_deposit) {
            return;
        }
        for (const line of this.currentOrder.unsentLines) {
            const depositProduct = line.product_id.product_tmpl_id.deposit_product_id;
            if (!depositProduct || line.deposit_main_line_id || line.depositLine) {
                continue;
            }
            const values = getOrderLineValues(this, depositProduct.product_tmpl_id, line.qty, "");
            const depositLine = this.models["pos.order.line"].create({
                ...values,
                deposit_main_line_id: line,
            });
            depositLine.full_product_name = depositProduct.name;
        }
    },

    isProductAvailable(product) {
        return !product.is_deposit && super.isProductAvailable(...arguments);
    },

    getDepositDisplayPrice(productTemplate) {
        const deposit = productTemplate.deposit_product_id;
        return deposit
            ? this.formatMonetary(this.getProductDisplayPrice(deposit.product_tmpl_id, deposit))
            : "";
    },
});
