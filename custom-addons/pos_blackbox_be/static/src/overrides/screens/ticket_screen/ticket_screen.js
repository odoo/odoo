/** @odoo-module **/

import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

/**
 * Prevent refunding work in/out lines.
 */
patch(TicketScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.numberBuffer = useService("number_buffer");
        this.notification = useService("pos_notification");
    },
    _onUpdateSelectedOrderline({ detail }) {
        if (this.pos.useBlackBoxBe()) {
            const order = this.getSelectedOrder();
            if (!order) {
                return this.numberBuffer.reset();
            }

            const selectedOrderlineId = this.getSelectedOrderlineId();
            const orderline = order.orderlines.find((line) => line.id == selectedOrderlineId);
            if (!orderline) {
                return this.numberBuffer.reset();
            }
            if (
                orderline.product.id === this.pos.workOutProduct.id ||
                orderline.product.id === this.pos.workInProduct.id
            ) {
                this.notification.add(_t("Refunding work in/out product is not allowed."), 5000);
                return;
            }
        }
        return super._onUpdateSelectedOrderline(...arguments);
    },
    async _onBeforeDeleteOrder(order) {
        if (this.pos.useBlackBoxBe() && !order.is_empty()) {
            /*
                Deleting an order in a certified POS involves registering the order as a PS.
                Then, registering it as a PR
                ultimately selling it as an NS at a price of 0.
            */
            try {
                this.pos.ui.block();
                let result = await this.pos.pushProFormaOrder(order, true);
                if (!result) {
                    return false;
                }
                for (const line of order.orderlines) {
                    line.set_quantity(line.get_quantity() * -1, true);
                }
                result = await this.pos.pushProFormaOrder(order, true);
                if (!result) {
                    return false;
                }
                order.orderlines = [];
                await this.pos.push_single_order(order);
            } finally {
                this.pos.ui.unblock();
            }
        }
        return await super._onBeforeDeleteOrder(...arguments);
    },
});
