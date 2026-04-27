import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { patch } from "@web/core/utils/patch";

patch(ControlButtons.prototype, {
    async clickPrintBill() {
        const order = this.pos.get_order();
        if (this.pos.useBlackBoxSweden()) {
            order.isProfo = true;
            order.receipt_type = "profo";
            const sequence = await this.pos.get_profo_order_sequence_number();
            order.sequence_number = sequence;

            await this.pos.pushSingleOrder(order);
            order.receipt_type = false;
        }
        await super.clickPrintBill(...arguments);
        order.isProfo = false;
    },
});
