import { patch } from "@web/core/utils/patch";
import { CartPage } from "@pos_self_order/app/pages/cart_page/cart_page";

patch(CartPage.prototype, {
    get lines() {
        return super.lines.filter((line) => !line.deposit_main_line_id);
    },

    changeQuantity(line, increase) {
        super.changeQuantity(line, increase);
        this.syncDepositQty(line);
    },

    removeLine(line, _event) {
        super.removeLine(...arguments);
        this.syncDepositQty(line);
    },

    syncDepositQty(line) {
        if (line.depositLine) {
            line.depositLine.qty = line.qty;
        }
    },

    getComboDepositPrice(line) {
        let total = 0;
        for (const comboLine of line.getAllLinesInCombo()) {
            const qty = this.getLineDisplayQty(comboLine);
            total += this.selfOrder.getLineDepositPrice(comboLine, qty);
        }
        return total;
    },

    get totalDepositPrice() {
        return this.lines.reduce((total, line) => total + this.getComboDepositPrice(line), 0);
    },
});
