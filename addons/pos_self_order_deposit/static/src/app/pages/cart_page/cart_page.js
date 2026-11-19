import { patch } from "@web/core/utils/patch";
import { CartPage } from "@pos_self_order/app/pages/cart_page/cart_page";

patch(CartPage.prototype, {
    get lines() {
        return super.lines.filter((line) => !line.deposit_main_line_id);
    },

    changeQuantity(line, increase) {
        super.changeQuantity(line, increase);
        if (line.depositLine) {
            line.depositLine.qty = line.qty;
        }
    },

    getPrice(line) {
        return super.getPrice(line) + this.getComboDepositPrice(line);
    },

    getLineDepositPrice(line) {
        return line.depositLine?.getDisplayPriceWithQty(this.getLineDisplayQty(line)) || 0;
    },

    getComboDepositPrice(line) {
        return line
            .getAllLinesInCombo()
            .reduce((total, comboLine) => total + this.getLineDepositPrice(comboLine), 0);
    },

    getDepositPrice(line) {
        return this.selfOrder.formatMonetary(this.getLineDepositPrice(line));
    },

    get totalDepositPrice() {
        return this.lines.reduce((total, line) => total + this.getComboDepositPrice(line), 0);
    },
});
