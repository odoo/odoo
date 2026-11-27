import { patch } from "@web/core/utils/patch";
import { SplitBillScreen } from "@pos_restaurant/app/screens/split_bill_screen/split_bill_screen";

patch(SplitBillScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.depositLineUuids = new Set();
    },

    onClickLine(line) {
        const mainLine = line.deposit_main_line_id || line;
        super.onClickLine(mainLine);
        for (const productLine of mainLine.getAllLinesInCombo()) {
            const selectedQty = this.qtyTracker[productLine.uuid] || 0;
            for (const depositLine of productLine.deposit_line_ids) {
                this.depositLineUuids.add(depositLine.uuid);
                this.qtyTracker[depositLine.uuid] = selectedQty;
                this.priceTracker[depositLine.uuid] =
                    (depositLine.prices.total_included / depositLine.qty) * selectedQty;
                this.setLineQtyStr(depositLine);
            }
        }
    },

    getNumberOfProducts() {
        // Deposit lines can be deleted while splitting, so they are tracked by uuid.
        return [...this.depositLineUuids].reduce(
            (count, uuid) => count - (this.qtyTracker[uuid] || 0),
            super.getNumberOfProducts()
        );
    },

    linkSplitLines(newLines) {
        super.linkSplitLines(...arguments);
        const lineByNewLine = new Map([...newLines].map(([line, newLine]) => [newLine, line]));
        for (const [line, newLine] of newLines) {
            const mainLine = lineByNewLine.get(newLine.deposit_main_line_id);
            if (mainLine) {
                line.deposit_main_line_id = mainLine;
            }
        }
    },
});
