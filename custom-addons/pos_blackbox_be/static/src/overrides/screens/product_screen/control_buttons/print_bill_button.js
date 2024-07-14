/** @odoo-module */
import { PrintBillButton } from "@pos_restaurant/app/control_buttons/print_bill_button/print_bill_button";
import { patch } from "@web/core/utils/patch";

patch(PrintBillButton.prototype, {
    async click() {
        const order = this.pos.get_order();
        if (this.pos.useBlackBoxBe() && order.get_orderlines().length > 0) {
            const result = await this.pos.pushProFormaOrder(order, true);
            if (!result) {
                return;
            }
        }
        await super.click();
    },
});
