import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { useBarcodeReader } from "@point_of_sale/app/barcode/barcode_reader_hook";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { ask } from "@point_of_sale/app/store/make_awaitable_dialog";
import { _t } from "@web/core/l10n/translation";

patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.notification = useService("notification");
        useBarcodeReader({
            coupon: this._onCouponScan,
        });
    },
    async _onCouponScan(code) {
        // IMPROVEMENT: Ability to understand if the scanned code is to be paid or to be redeemed.
        const res = await this.pos.activateCode(code.base_code);
        if (res !== true) {
            this.notification.add(res, { type: "danger" });
        }
    },
    async _barcodeProductAction(code) {
        await super._barcodeProductAction(code);
        this.pos.updateRewards();
    },
    async _barcodeGS1Action(code) {
        await super._barcodeGS1Action(code);
        this.pos.updateRewards();
    },
    async updateSelectedOrderline(key) {
        const selectedLine = this.currentOrder.get_selected_orderline();
        if (key === "-") {
            if (selectedLine && selectedLine._e_wallet_program_id) {
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
            const reward = selectedLine.reward_id;
            const confirmed = await ask(this.dialog, {
                title: _t("Deactivating reward"),
                body: _t(
                    "Are you sure you want to remove %s from this order?\n You will still be able to claim it through the reward button.",
                    reward.description
                ),
                cancelLabel: _t("No"),
                confirmLabel: _t("Yes"),
            });
            if (confirmed) {
                this.state.numberBuffer = null;
            } else {
                // Cancel backspace
                return;
            }
        }
        return super.updateSelectedOrderline(key);
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
        if (!selectedLine) {
            return;
        }
        if (selectedLine.is_reward_line && val === "remove") {
            this.currentOrder.uiState.disabledRewards.add(selectedLine.reward_id.id);
            const coupon = selectedLine.coupon_id;
            if (
                coupon &&
                coupon.id > 0 &&
                this.currentOrder._code_activated_coupon_ids.find((c) => c.code === coupon.code)
            ) {
                coupon.delete();
            }
        }
        if (
            !selectedLine ||
            !selectedLine.is_reward_line ||
            (selectedLine.is_reward_line && ["", "remove"].includes(val))
        ) {
            super._setValue(val);
        }
        if (!selectedLine.is_reward_line || (selectedLine.is_reward_line && val === "remove")) {
            this.pos.updateRewards();
        }
    },

    async _showDecreaseQuantityPopup() {
        const result = await super._showDecreaseQuantityPopup();
        if (result) {
            this.pos.updateRewards();
        }
    },
});
