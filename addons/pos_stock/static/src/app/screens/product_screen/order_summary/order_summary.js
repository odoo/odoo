import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { patch } from "@web/core/utils/patch";

patch(OrderSummary.prototype, {
    async editPackLotLines(line) {
        const isAllowOnlyOneLot = line.product_id.isAllowOnlyOneLot();
        let editedPackLotLines = [];
        if (line.refunded_orderline_id) {
            editedPackLotLines = await this.pos.editLotsRefund(line);
        } else {
            editedPackLotLines = await this.pos.editLots(
                line.product_id,
                line.getPackLotLinesToEdit(isAllowOnlyOneLot)
            );
        }
        line.editPackLotLines(editedPackLotLines);
    },
});
