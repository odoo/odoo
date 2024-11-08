import { _t } from "@web/core/l10n/translation";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

/**
 * Prevent refunding ewallet/gift card lines.
 */
patch(TicketScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.notification = useService("notification");
    },
    _onUpdateSelectedOrderline() {
        const order = this.getSelectedOrder();
        if (!order) {
            return this.numberBuffer.reset();
        }
        const selectedOrderlineId = this.getSelectedOrderlineId();
        const orderline = order.lines.find((line) => line.id == selectedOrderlineId);
        if (orderline && this._isEWalletGiftCard(orderline)) {
            this._showNotAllowedRefundNotification();
            return this.numberBuffer.reset();
        }
        return super._onUpdateSelectedOrderline(...arguments);
    },
    _prepareAutoRefundOnOrder(order) {
        const selectedOrderlineId = this.getSelectedOrderlineId();
        const orderline = order.lines.find((line) => line.id == selectedOrderlineId);
        if (this._isEWalletGiftCard(orderline)) {
            this._showNotAllowedRefundNotification();
            return false;
        }
        return super._prepareAutoRefundOnOrder(...arguments);
    },
    _showNotAllowedRefundNotification() {
        this.notification.add(
            _t(
                "Refunding a top up or reward product for an eWallet or gift card program is not allowed."
            ),
            5000
        );
    },
    _isEWalletGiftCard(orderline) {
        const linkedProgramIds = this.pos.models["loyalty.program"].getBy(
            "trigger_product_ids",
            orderline.product_id.id
        );
        if (linkedProgramIds) {
            return linkedProgramIds.length > 0;
        }
        if (orderline.is_reward_line) {
            const reward = orderline.reward_id;
            const program = reward && reward.program_id;
            if (program && ["gift_card", "ewallet"].includes(program.program_type)) {
                return true;
            }
        }
        return false;
    },
});
