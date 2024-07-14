/** @odoo-module */
import { PrintBillButton } from "@pos_restaurant/app/control_buttons/print_bill_button/print_bill_button";
import { patch } from "@web/core/utils/patch";

patch(PrintBillButton.prototype, {
    async onClick() {
        const order = this.pos.get_order();
        if (this.pos.useBlackBoxSweden()) {
            order.isProfo = true;
            order.receipt_type = "profo";
            const sequence = await this.pos.get_profo_order_sequence_number();
            order.sequence_number = sequence;

            await this.pos.push_single_order(order);
            order.receipt_type = false;
        }
        await super.onClick(...arguments);
        order.isProfo = false;
    },
});
