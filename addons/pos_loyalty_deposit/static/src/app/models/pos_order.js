import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    applyReward(reward) {
        super.applyReward(...arguments);
        if (!this.config.module_pos_deposit || reward.reward_type !== "product") {
            return;
        }
        for (const line of this.lines) {
            const depositProduct = line.product_id.deposit_product_id;
            if (line.reward_id !== reward || !depositProduct || line.depositLine) {
                continue;
            }
            this.models["pos.order.line"]
                .create({
                    order_id: this,
                    product_id: depositProduct,
                    tax_ids: [...depositProduct.taxes_id],
                    qty: line.qty,
                    price_type: "original",
                    deposit_main_line_id: line,
                    // course_id is only available when pos_restaurant is installed
                    course_id: line.course_id,
                })
                .recomputeUnitPrice();
        }
    },

    removeOrderline(line, deep = true) {
        const mainLine = line.deposit_main_line_id || line;
        if (!mainLine.is_reward_line) {
            return super.removeOrderline(...arguments);
        }
        // Deleted here so that pos_deposit does not delete it a second time.
        mainLine.depositLine?.delete();
        return super.removeOrderline(mainLine, deep);
    },
});
