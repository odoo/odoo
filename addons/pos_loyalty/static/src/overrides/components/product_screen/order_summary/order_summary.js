/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { patch } from "@web/core/utils/patch";
import { ask } from "@point_of_sale/app/store/make_awaitable_dialog";
import { useService } from "@web/core/utils/hooks";

patch(OrderSummary.prototype, {
    setup() {
        super.setup(...arguments);
        this.notification = useService("pos_notification");
    },
    async updateSelectedOrderline({ buffer, key }) {
        const selectedLine = this.currentOrder.get_selected_orderline();
        if (key === "-") {
            if (selectedLine && selectedLine.eWalletGiftCardProgram) {
                // Do not allow negative quantity or price in a gift card or ewallet orderline.
                // Refunding gift card or ewallet is not supported.
                this.notification.add(
                    _t("You cannot set negative quantity or price to gift card or ewallet."),
                    4000
                );
                return;
            }
        }
        if (
            selectedLine &&
            selectedLine.is_reward_line &&
            !selectedLine.manual_reward &&
            (key === "Backspace" || key === "Delete")
        ) {
            const reward = this.pos.models["loyalty.reward"].get(selectedLine.reward_id);
            const confirmed = await ask(this.dialog, {
                title: _t("Deactivating reward"),
                body: _t(
                    "Are you sure you want to remove %s from this order?\n You will still be able to claim it through the reward button.",
                    reward.description
                ),
                cancelText: _t("No"),
                confirmText: _t("Yes"),
            });
            if (confirmed) {
                buffer = null;
            } else {
                // Cancel backspace
                return;
            }
        }
        return super.updateSelectedOrderline({ buffer, key });
    },
    /**
     * 1/ Perform the usual set value operation (super._setValue(val)) if the line being modified
     * is not a reward line or if it is a reward line, the `val` being set is '' or 'remove' only.
     *
     * 2/ Update activated programs and coupons when removing a reward line.
     *
     * 3/ Trigger 'update-rewards' if the line being modified is a regular line or
     * if removing a reward line.
     *
     * @override
     */
    _setValue(val) {
        const selectedLine = this.currentOrder.get_selected_orderline();
        if (
            !selectedLine ||
            !selectedLine.is_reward_line ||
            (selectedLine.is_reward_line && ["", "remove"].includes(val))
        ) {
            super._setValue(val);
        }
        if (!selectedLine) {
            return;
        }
        if (selectedLine.is_reward_line && val === "remove") {
            this.currentOrder.disabledRewards.add(selectedLine.reward_id);
            const { couponCache } = this.pos;
            const coupon = couponCache[selectedLine.coupon_id];
            if (
                coupon &&
                coupon.id > 0 &&
                this.currentOrder.codeActivatedCoupons.find((c) => c.code === coupon.code)
            ) {
                delete couponCache[selectedLine.coupon_id];
                this.currentOrder.codeActivatedCoupons.splice(
                    this.currentOrder.codeActivatedCoupons.findIndex((coupon) => {
                        return coupon.id === selectedLine.coupon_id;
                    }),
                    1
                );
            }
        }
        if (!selectedLine.is_reward_line || (selectedLine.is_reward_line && val === "remove")) {
            this.currentOrder._updateRewards();
        }
    },

    async _showDecreaseQuantityPopup() {
        const result = await super._showDecreaseQuantityPopup();
        if (result) {
            this.currentOrder._updateRewards();
        }
    },
});
