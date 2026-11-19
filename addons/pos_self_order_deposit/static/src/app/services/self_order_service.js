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
            const depositProduct = line.product_id.deposit_product_id;
            if (!depositProduct || line.depositLine) {
                continue;
            }
            this.models["pos.order.line"].create({
                ...getOrderLineValues(this, depositProduct.product_tmpl_id, line.qty, ""),
                deposit_main_line_id: line,
                full_product_name: depositProduct.name,
            });
        }
    },

    calculateOrderLineTotals(changes) {
        const totals = super.calculateOrderLineTotals(changes);
        for (const [uuid, { qty }] of Object.entries(changes)) {
            if (
                qty > 0 &&
                this.models["pos.order.line"].getBy("uuid", uuid)?.deposit_main_line_id
            ) {
                totals.count -= qty;
            }
        }
        return totals;
    },

    skipCartVerification(line) {
        return Boolean(line.deposit_main_line_id) || super.skipCartVerification(...arguments);
    },

    isProductAvailable(product) {
        return !product.is_deposit && super.isProductAvailable(...arguments);
    },

    getSharedDepositProduct(variants) {
        const deposit = variants[0]?.deposit_product_id;
        const isShared = variants.every((variant) => variant.deposit_product_id === deposit);
        return this.config.module_pos_deposit && isShared && deposit;
    },

    getAttributeValueDepositProduct(productTemplate, attributeValue) {
        return this.getSharedDepositProduct(
            productTemplate.product_variant_ids.filter((variant) =>
                variant.product_template_variant_value_ids.includes(attributeValue)
            )
        );
    },

    getDepositDisplayPrice(deposit) {
        return this.formatMonetary(this.getProductDisplayPrice(deposit.product_tmpl_id, deposit));
    },
});
