/** @odoo-module **/

import TicketScreen from "@point_of_sale/js/Screens/TicketScreen/TicketScreen";
import Registries from "@point_of_sale/js/Registries";
import NumberBuffer from "@point_of_sale/js/Misc/NumberBuffer";

/**
 * Prevent refunding ewallet/gift card lines.
 */
export const PosLoyaltyTicketScreen = (TicketScreen) =>
    class PosLoyaltyTicketScreen extends TicketScreen {
        _onUpdateSelectedOrderline() {
            const order = this.getSelectedSyncedOrder();
            if (!order) {
                return NumberBuffer.reset();
            }
            const selectedOrderlineId = this.getSelectedOrderlineId();
            const orderline = order.orderlines.find((line) => line.id == selectedOrderlineId);
            if (orderline && this._isEWalletGiftCard(orderline)) {
                this._showNotAllowedRefundNotification();
                return NumberBuffer.reset();
            }
            return super._onUpdateSelectedOrderline(...arguments);
        }
        _prepareAutoRefundOnOrder(order) {
            const selectedOrderlineId = this.getSelectedOrderlineId();
            const orderline = order.orderlines.find((line) => line.id == selectedOrderlineId);
            if (this._isEWalletGiftCard(orderline)) {
                this._showNotAllowedRefundNotification();
                return false;
            }
            return super._prepareAutoRefundOnOrder(...arguments);
        }
        _showNotAllowedRefundNotification() {
            this.showNotification(
                this.env._t(
                    "Refunding a top up or reward product for an eWallet or gift card program is not allowed."
                ),
                5000
            );
        }
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
        }
    };

Registries.Component.extend(TicketScreen, PosLoyaltyTicketScreen);
