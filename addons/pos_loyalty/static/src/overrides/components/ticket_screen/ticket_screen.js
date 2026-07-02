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
        return this.pos.models["loyalty.program"].some(
            (program) =>
                ["gift_card", "ewallet"].includes(program.program_type) &&
                program.trigger_product_ids.map((p) => p.id).includes(orderline.product_id.id)
        );
    },
    async _setOrder() {
        await super._setOrder(...arguments);
        if (this.pos.isOpenOrderShareable()) {
            this.pos.updateRewards();
        }
    },
    /**
     * After building the refund order, log for debugging.
     * The actual loyalty point reversal happens in two places:
     * 1. Display: _updateProgramsForRefund() in pos_store.js (reactive, runs when order changes)
     * 2. Persistence: _reverse_loyalty_points_for_refund() in pos_order.py (server-side, on payment)
     *
     * @override
     */
    async addAdditionalRefundInfo(order, destinationOrder) {
        await super.addAdditionalRefundInfo(...arguments);
    },
    /**
     * Seeds couponPointChanges on the refund order with negated point values
     * from the original order so that _postProcessLoyalty will deduct them.
     *
     * Only loyalty-type programs are reversed here; gift cards and ewallets
     * are handled separately (they are blocked from refund above).
     */
    _reverseLoyaltyPointsForRefund(originalOrder, refundOrder) {
        const originalChanges = originalOrder.uiState?.couponPointChanges || {};
        if (!Object.keys(originalChanges).length) {
            return;
        }

        // Determine the ratio of the refund vs the original order so partial
        // refunds deduct the proportional share of points.
        const originalTotal = Math.abs(originalOrder.get_total_with_tax());
        const refundTotal = Math.abs(refundOrder.get_total_with_tax());
        const ratio = originalTotal > 0 ? Math.min(refundTotal / originalTotal, 1) : 1;

        for (const pointChange of Object.values(originalChanges)) {
            const program = this.pos.models["loyalty.program"].get(pointChange.program_id);
            if (!program) {
                continue;
            }
            // Only reverse loyalty programs; skip gift_card / ewallet.
            if (!["loyalty", "next_order_coupons", "coupons"].includes(program.program_type)) {
                continue;
            }
            const pointsToReverse = parseFloat((pointChange.points * ratio).toFixed(2));
            if (pointsToReverse === 0) {
                continue;
            }
            const existingChange = refundOrder.uiState.couponPointChanges[pointChange.coupon_id];
            if (existingChange) {
                existingChange.points -= pointsToReverse;
            } else {
                refundOrder.uiState.couponPointChanges[pointChange.coupon_id] = {
                    points: -pointsToReverse,
                    program_id: pointChange.program_id,
                    coupon_id: pointChange.coupon_id,
                    barcode: pointChange.barcode || false,
                    appliedRules: pointChange.appliedRules || [],
                };
            }
        }
    },
});
