import { _t } from "@web/core/l10n/translation";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { patch } from "@web/core/utils/patch";
import { ask } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ManageGiftCardPopup } from "@pos_loyalty/app/components/popups/manage_giftcard_popup/manage_giftcard_popup";

patch(OrderSummary.prototype, {
    setup() {
        super.setup(...arguments);
        this.notification = useService("notification");
    },
    async updateSelectedOrderline({ buffer, key }) {
        const selectedLine = this.currentOrder.getSelectedOrderline();
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
        const selectedLine = this.currentOrder.getSelectedOrderline();
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

    /**
     * Updates the order line with the gift card information:
     * 1. Reduce the quantity if greater than one, otherwise remove the order line.
     * 2. Add a new order line with updated gift card code and points, removing any existing related couponPointChanges.
     */
    async _updateGiftCardOrderline(code, points) {
        let selectedLine = this.currentOrder.getSelectedOrderline();
        const product = selectedLine.product_id;

        if (selectedLine.getQuantity() > 1) {
            selectedLine.setQuantity(selectedLine.getQuantity() - 1);
        } else {
            this.currentOrder.removeOrderline(selectedLine);
        }

        const program = this.pos.models["loyalty.program"].find(
            (p) => p.program_type === "gift_card"
        );
        const existingCouponIds = Object.keys(this.currentOrder.uiState.couponPointChanges).filter(
            (key) => {
                const change = this.currentOrder.uiState.couponPointChanges[key];
                return (
                    change.points === product.lst_price &&
                    change.program_id === program.id &&
                    change.product_id === product.id &&
                    !change.manual
                );
            }
        );
        if (existingCouponIds.length) {
            const couponId = existingCouponIds.shift();
            delete this.currentOrder.uiState.couponPointChanges[couponId];
        }

        await this.pos.addLineToCurrentOrder(
            { product_id: product, product_tmpl_id: product.product_tmpl_id },
            { price_unit: points }
        );
        selectedLine = this.currentOrder.getSelectedOrderline();
        selectedLine.gift_code = code;
    },

    manageGiftCard() {
        this.dialog.add(ManageGiftCardPopup, {
            title: _t("Sell/Manage physical gift card"),
            placeholder: _t("Enter Gift Card Number"),
            getPayload: async (code, points, expirationDate) => {
                points = parseFloat(points);
                if (isNaN(points)) {
                    console.error("Invalid amount value:", points);
                    return;
                }
                code = code.trim();
                const res = await this.pos.data.searchRead(
                    "loyalty.card",
                    ["&", ["program_type", "=", "gift_card"], ["code", "=", code]],
                    []
                );
                if (res.length > 0) {
                    this.notification.add(_t("This Gift card is already been sold."), {
                        type: "danger",
                    });
                    return;
                }

                // check for duplicate code
                if (this.currentOrder.duplicateCouponChanges(code)) {
                    this.dialog.add(ConfirmationDialog, {
                        title: _t("Validation Error"),
                        body: _t("A coupon/loyalty card must have a unique code."),
                    });
                    return;
                }

                await this._updateGiftCardOrderline(code, points);
                this.currentOrder.processGiftCard(code, points, expirationDate);

                // update indexedDB
                this.pos.data.synchronizeLocalDataInIndexedDB();
            },
        });
    },

    clickLine(ev, orderline) {
        if (orderline.isSelected() && orderline.getEWalletGiftCardProgramType() === "gift_card") {
            return;
        } else {
            super.clickLine(ev, orderline);
        }
    },
});
