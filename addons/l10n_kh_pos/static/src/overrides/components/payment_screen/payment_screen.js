/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    async _postPushOrderResolve(order, order_server_ids) {
        if (this.pos.config.khmer_receipt && order.is_to_invoice()) {
            const move = await this.orm.searchRead(
                "account.move",
                [["pos_order_ids", "in", order_server_ids]],
                ["name"]
            );
            order.set_invoice_name(move[0].name);
        }
        return super._postPushOrderResolve(...arguments);
    },
})
