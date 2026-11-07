import { patch } from "@web/core/utils/patch";
import { CartPage } from "@pos_self_order/app/pages/cart_page/cart_page";

patch(CartPage.prototype, {
    get lines() {
        return super.lines.filter((line) => !line.deposit_main_line_id);
    },

    changeQuantity(line, increase) {
        super.changeQuantity(line, increase);
        if (!this.selfOrder.currentOrder.lines.includes(line)) {
            return;
        }
        for (const mainLine of [line, ...line.combo_line_ids]) {
            const deposit = mainLine.depositLine;
            if (deposit) {
                deposit.qty = mainLine.qty;
            }
        }
    },

    getPrice(line) {
        let price = super.getPrice(line);
        for (const mainLine of [line, ...line.combo_line_ids]) {
            const deposit = mainLine.depositLine;
            if (deposit) {
                price += deposit.getDisplayPriceWithQty(this.getLineDisplayQty(mainLine));
            }
        }
        return price;
    },

    getDepositPrice(line) {
        return this.selfOrder.formatMonetary(
            line.depositLine.getDisplayPriceWithQty(this.getLineDisplayQty(line))
        );
    },
});
