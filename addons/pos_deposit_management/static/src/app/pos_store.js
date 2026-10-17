import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    async addLineToOrder(vals, order, opts = {}, configure = true) {
        const line = await super.addLineToOrder(vals, order, opts, configure);
        if (!line || opts.isDepositLine) {
            return line;
        }
        const mainLines = line.combo_line_ids?.length ? [...line.combo_line_ids] : [line];
        for (const mainLine of mainLines) {
            await this._addDepositLine(mainLine, order);
        }
        this.selectOrderLine(order, line);
        return line;
    },

    async _addDepositLine(mainLine, order) {
        if (mainLine._depositLine) {
            return;
        }
        const depositProduct = mainLine.product_id?.product_tmpl_id?.deposit_product_id;
        if (!depositProduct) {
            return;
        }
        order._creatingDepositLine = true;
        let depositLine;
        try {
            depositLine = await this.addLineToOrder(
                {
                    product_tmpl_id: depositProduct.product_tmpl_id,
                    product_id: depositProduct,
                    qty: mainLine.qty,
                },
                order,
                { isDepositLine: true },
                false
            );
        } finally {
            order._creatingDepositLine = false;
        }
        if (depositLine && depositLine !== mainLine) {
            mainLine._depositLine = depositLine;
            depositLine._mainLine = mainLine;
        }
    },
});
