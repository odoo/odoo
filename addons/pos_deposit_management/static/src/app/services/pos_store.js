import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    async addLineToOrder(vals, order, opts = {}, configure = true) {
        const line = await super.addLineToOrder(vals, order, opts, configure);
        if (!this.config.module_pos_deposit_management || !line || vals.deposit_main_line_id) {
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
    },
});
