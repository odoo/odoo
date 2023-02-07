/** @odoo-module **/

import { TicketScreen } from "@point_of_sale/js/Screens/TicketScreen/TicketScreen";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

/**
 * Prevent refunding ewallet/gift card lines.
 */
patch(TicketScreen.prototype, "pos_loyalty.TicketScreen", {
    setup() {
        this._super(...arguments);
        this.notification = useService("pos_notification");
    },
    _onUpdateSelectedOrderline() {
        const order = this.getSelectedSyncedOrder();
        if (!order) {
            return this.numberBuffer.reset();
        }
        const selectedOrderlineId = this.getSelectedOrderlineId();
        const orderline = order.orderlines.find((line) => line.id == selectedOrderlineId);
        if (orderline && this._isEWalletGiftCard(orderline)) {
            this._showNotAllowedRefundNotification();
            return this.numberBuffer.reset();
        }
        return this._super(...arguments);
    },
    _prepareAutoRefundOnOrder(order) {
        const selectedOrderlineId = this.getSelectedOrderlineId();
        const orderline = order.orderlines.find((line) => line.id == selectedOrderlineId);
        if (this._isEWalletGiftCard(orderline)) {
            this._showNotAllowedRefundNotification();
            return false;
        }
        return this._super(...arguments);
    },
    _showNotAllowedRefundNotification() {
        this.notification.add(
            this.env._t(
                "Refunding a top up or reward product for an eWallet or gift card program is not allowed."
            ),
            5000
        );
    },
    _isEWalletGiftCard(orderline) {
        const linkedProgramIds = this.env.pos.productId2ProgramIds[orderline.product.id];
        if (linkedProgramIds) {
            return linkedProgramIds.length > 0;
        }
        if (orderline.is_reward_line) {
            const reward = this.env.pos.reward_by_id[orderline.reward_id];
            const program = reward && reward.program_id;
            if (program && ["gift_card", "ewallet"].includes(program.program_type)) {
                return true;
            }
        }
        return false;
    },
});
