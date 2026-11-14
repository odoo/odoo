import { patch } from "@web/core/utils/patch";
import { SplitBillScreen } from "@pos_restaurant/app/screens/split_bill_screen/split_bill_screen";

patch(SplitBillScreen.prototype, {
    onClickLine(line) {
        const mainLine = line.deposit_main_line_id || line;
        const comboParent = mainLine.combo_parent_id || mainLine;

        super.onClickLine(comboParent);

        const comboLines = [comboParent, ...(comboParent.combo_line_ids || [])];

        for (const productLine of comboLines) {
            const depositLine = productLine.depositLine;
            if (!depositLine) {
                continue;
            }

            const selectedQty = this.qtyTracker[productLine.uuid] || 0;

            this.qtyTracker[depositLine.uuid] = selectedQty;
            this.priceTracker[depositLine.uuid] = depositLine.qty
                ? (depositLine.prices.total_included / depositLine.qty) * selectedQty
                : 0;

            this.setLineQtyStr(depositLine);
        }
    },
});
