/** @odoo-module **/

import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { useBarcodeReader } from "@point_of_sale/js/custom_hooks";
import { patch } from "@web/core/utils/patch";
import { ConfirmPopup } from "@point_of_sale/js/Popups/ConfirmPopup";
import { useService } from "@web/core/utils/hooks";

patch(ProductScreen.prototype, "pos_loyalty.ProductScreen", {
    setup() {
        this._super(...arguments);
        this.notification = useService("pos_notification");
        useBarcodeReader({
            coupon: this._onCouponScan,
        });
    },
    async onClickPay() {
        const order = this.env.pos.get_order();
        const eWalletLine = order
            .get_orderlines()
            .find((line) => line.getEWalletGiftCardProgramType() === "ewallet");
        if (eWalletLine && !order.get_partner()) {
            const { confirmed } = await this.popup.add(ConfirmPopup, {
                title: this.env._t("Customer needed"),
                body: this.env._t("eWallet requires a customer to be selected"),
            });
            if (confirmed) {
                const { confirmed, payload: newPartner } = await this.pos.showTempScreen(
                    "PartnerListScreen",
                    { partner: null }
                );
                if (confirmed) {
                    order.set_partner(newPartner);
                    order.updatePricelist(newPartner);
                }
            }
        } else {
            return this._super(...arguments);
        }
    },
    _onCouponScan(code) {
        // IMPROVEMENT: Ability to understand if the scanned code is to be paid or to be redeemed.
        this.currentOrder.activateCode(code.base_code);
    },
    async updateSelectedOrderline({ buffer, key }) {
        const _super = this._super;
        const selectedLine = this.currentOrder.get_selected_orderline();
        if (key === "-") {
            if (selectedLine.eWalletGiftCardProgram) {
                // Do not allow negative quantity or price in a gift card or ewallet orderline.
                // Refunding gift card or ewallet is not supported.
                this.notification.add(
                    this.env._t(
                        "You cannot set negative quantity or price to gift card or ewallet."
                    ),
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
            const reward = this.env.pos.reward_by_id[selectedLine.reward_id];
            const { confirmed } = await this.popup.add(ConfirmPopup, {
                title: this.env._t("Deactivating reward"),
                body: _.str.sprintf(
                    this.env._t(
                        "Are you sure you want to remove %s from this order?\n You will still be able to claim it through the reward button."
                    ),
                    reward.description
                ),
                cancelText: this.env._t("No"),
                confirmText: this.env._t("Yes"),
            });
            if (confirmed) {
                buffer = null;
            } else {
                // Cancel backspace
                return;
            }
        }
        return _super({ buffer, key });
    },
    /**
     * 1/ Perform the usual set value operation (this._super(val)) if the line being modified
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
            this._super(val);
        }
        if (!selectedLine) {
            return;
        }
        if (selectedLine.is_reward_line && val === "remove") {
            this.currentOrder.disabledRewards.add(selectedLine.reward_id);
            const coupon = this.env.pos.couponCache[selectedLine.coupon_id];
            if (
                coupon &&
                coupon.id > 0 &&
                this.currentOrder.codeActivatedCoupons.find((c) => c.code === coupon.code)
            ) {
                delete this.env.pos.couponCache[selectedLine.coupon_id];
                this.currentOrder.codeActivatedCoupons.splice(
                    this.currentOrder.codeActivatedCoupons.findIndex((coupon) => {
                        return coupon.id === selectedLine.coupon_id;
                    }),
                    1
                );
            }
        }
        if (!selectedLine.is_reward_line || (selectedLine.is_reward_line && val === "remove")) {
            selectedLine.order._updateRewards();
        }
    },
});
