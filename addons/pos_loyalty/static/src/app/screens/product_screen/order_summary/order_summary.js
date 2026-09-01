import { _t } from "@web/core/l10n/translation";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ManageGiftCardPopup } from "@pos_loyalty/app/components/popups/manage_giftcard_popup/manage_giftcard_popup";
import { roundPrecision } from "@web/core/utils/numbers";

patch(OrderSummary.prototype, {
    /**
     * A loyalty reward line removes itself as soon as its quantity reaches 0 (see the
     * `pos.order.line` setQuantity override), which then auto-selects the next line. This
     * will reset the numpad buffer whenever a line is removed
     */
    async updateSelectedOrderline(params) {
        const order = this.pos.getOrder();
        const editedLine = order?.getSelectedOrderline();
        if (
            editedLine?.gift_card_vals?.code &&
            params.key !== "Backspace" &&
            params.key !== "Delete"
        ) {
            this.dialog.add(AlertDialog, {
                title: _t("Gift Card"),
                body: _t("You cannot change the quantity or the price of a physical gift card."),
            });
            return;
        }
        const editedRewardId = editedLine?.is_reward_line ? editedLine.reward_id?.id : null;
        await super.updateSelectedOrderline(params);
        if (
            editedRewardId &&
            order &&
            !order.getOrderlines().some((line) => line.reward_id?.id === editedRewardId)
        ) {
            this.numberBuffer.reset();
            this.pos.numpadMode = "quantity";
        }
    },
    roundPoints(points) {
        return roundPrecision(points, 0.01);
    },
    /**
     * Turn a gift-card sale line into a physical gift card: the cashier enters the card's
     * printed code and amount. The code is written on `gift_card_vals` and passed to the
     * server, which creates the real card from it when the order is saved.
     */
<<<<<<< 3b5ffdc4184b25128fa8204bccffcce82cad345e
||||||| df947972f49099b7cd5638f4d277f36d19339b2c
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

=======
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
        const program = selectedLine._e_wallet_program_id;

        if (selectedLine.getQuantity() > 1) {
            selectedLine.setQuantity(selectedLine.getQuantity() - 1);
        } else {
            this.currentOrder.removeOrderline(selectedLine);
        }

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
            { price_unit: points, eWalletGiftCardProgram: program }
        );
        selectedLine = this.currentOrder.getSelectedOrderline();
        selectedLine.gift_code = code;
    },

>>>>>>> 5c7cedf731ae735be0ce2fdd1edd306f3230697c
    manageGiftCard(line) {
        this.dialog.add(ManageGiftCardPopup, {
            title: _t("Sell/Manage physical gift card"),
            placeholder: _t("Enter Gift Card Number"),
            line,
            getPayload: (code, amount, expirationDate) => {
                code = code.trim();
                amount = parseFloat(amount);
                if (isNaN(amount)) {
                    return;
                }
                // A card code is unique: reject it when another line on this order already
                // claims it, otherwise both lines would try to create the same card.
                const duplicate = this.currentOrder
                    .getOrderlines()
                    .some((other) => other !== line && other.gift_card_vals?.code === code);
                if (duplicate) {
                    this.dialog.add(AlertDialog, {
                        title: _t("Validation Error"),
                        body: _t("A coupon/loyalty card must have a unique code."),
                    });
                    return;
                }
                line.setUnitPrice(amount);
                line.gift_card_vals = {
                    ...line.gift_card_vals,
                    code,
                    expiration_date: expirationDate,
                };
                this.pos.selectOrderLine(this.currentOrder, line);
            },
        });
    },
});
