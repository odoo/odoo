import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    async addLineToOrder(vals, order, opts = {}, configure = true) {
        const line = await super.addLineToOrder(vals, order, opts, configure);
        if (!this.config.module_pos_deposit || !line || vals.deposit_main_line_id) {
            return line;
        }
        const mainLines = [line, ...line.combo_line_ids].filter(
            (l) => l.product_id.deposit_product_id && !l.depositLine
        );
        for (const mainLine of mainLines) {
            const depositProduct = mainLine.product_id.deposit_product_id;
            await this.addLineToOrder(
                {
                    product_tmpl_id: depositProduct.product_tmpl_id,
                    product_id: depositProduct,
                    qty: mainLine.qty,
                    deposit_main_line_id: mainLine,
                },
                order,
                {},
                false
            );
        }
        if (mainLines.length) {
            this.selectOrderLine(order, line);
        }
        return line;
    },

    filterExcludedProducts(products) {
        const candidates = [...products];
        const filtered = super.filterExcludedProducts(candidates);
        const displayed = new Set(filtered);
        return [
            ...filtered,
            ...candidates.filter((p) => p.is_deposit && p.canBeDisplayed && !displayed.has(p)),
        ];
    },
});
