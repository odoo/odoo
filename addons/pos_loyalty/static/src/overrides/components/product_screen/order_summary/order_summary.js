import { _t } from "@web/core/l10n/translation";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { patch } from "@web/core/utils/patch";
import { ask, makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { useService } from "@web/core/utils/hooks";
import { ManageGiftCardPopup } from "@pos_loyalty/app/popup/manage_giftcard_popup/manage_giftcard_popup";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(OrderSummary.prototype, {
    setup() {
        super.setup(...arguments);
        this.notification = useService("notification");
        this.dialog = useService("dialog");
    },
    async updateSelectedOrderline({ buffer, key }) {
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
                buffer = null;
            } else {
                // Cancel backspace
                return;
            }
        }
        return super.updateSelectedOrderline({ buffer, key });
    },
    async handlePhysicalGiftCard(line) {
        const giftCardProduct = line.product_id;
        const data = await makeAwaitable(this.dialog, ManageGiftCardPopup, {
            title: _t("Sell/Manage physical gift card"),
            placeholder: _t("Enter Gift Card Number"),
        });

        const res = await this.pos.data.searchRead(
            "loyalty.card",
            ["&", ["program_type", "=", "gift_card"], ["code", "=", data.code]],
            []
        );

        if (this.currentOrder.duplicateCouponChanges(data.code)) {
            this.dialog.add(ConfirmationDialog, {
                title: _t("Validation Error"),
                body: _t("A coupon/loyalty card must have a unique code."),
            });
            return;
        }

        let giftCard;
        if (!res.length) {
            giftCard = this.pos.models["loyalty.card"].create({
                code: data.code,
                program_type: "gift_card",
                amount: data.amount,
            });
        } else {
            giftCard = res[0];
        }

        line.delete();
        await this.pos.addLineToCurrentOrder(
            {
                product_id: giftCardProduct,
                quantity: 1,
                price_unit: data.amount,
            },
            {
                giftCardManual: true,
                giftCardCode: data.code,
                giftCardId: giftCard,
            }
        );

        // This will automatically update coupon point changes.
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
