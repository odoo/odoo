import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    async addLineToOrder(vals, order, opts = {}, configure = true) {
        const line = await super.addLineToOrder(vals, order, opts, configure);
        if (!this.config.module_pos_deposit || !line || vals.deposit_main_line_id) {
            return line;
        }
        for (const mainLine of [line, ...line.combo_line_ids]) {
            await this._addDepositLine(mainLine, order);
        }
        this.selectOrderLine(order, line);
        return line;
    },

    async _addDepositLine(mainLine, order) {
        const depositProduct = mainLine.product_id.product_tmpl_id.deposit_product_id;
        if (depositProduct && !mainLine.depositLine) {
            const depositLine = await this.addLineToOrder(
                {
                    product_tmpl_id: depositProduct.product_tmpl_id,
                    product_id: depositProduct,
                    qty: mainLine.qty,
                    deposit_main_line_id: mainLine,
                    course_id: mainLine.course_id?.id,
                },
                order,
                {},
                false
            );
            return depositLine;
        }
    },

    filterExcludedProducts(products) {
        const candidates = Array.isArray(products) ? products : [...products];
        const filtered = super.filterExcludedProducts(candidates);
        const displayed = new Set(filtered);
        const excludedIds = new Set(this.getExcludedProductIds());
        const deposits = candidates.filter(
            (p) => p.is_deposit && !displayed.has(p) && !excludedIds.has(p.id) && p.canBeDisplayed
        );
        return deposits.length ? [...filtered, ...deposits] : filtered;
    },
});
