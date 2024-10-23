import { _t } from "@web/core/l10n/translation";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ManageGiftCardPopup } from "@pos_loyalty/utils/manage_giftcard_popup/manage_giftcard_popup";

patch(OrderSummary.prototype, {
    setup() {
        super.setup(...arguments);
        this.notification = useService("notification");
    },

    /**
     * Updates the order line with the gift card information:
     * 1. Reduce the quantity if greater than one, otherwise remove the order line.
     * 2. Add a new order line with updated gift card code and points, removing any existing related couponPointChanges.
     */
    async _updateGiftCardOrderline(code, points) {
        let selectedLine = this.currentOrder.get_selected_orderline();
        const product = selectedLine.product_id;

        if (selectedLine.get_quantity() > 1) {
            selectedLine.set_quantity(selectedLine.get_quantity() - 1);
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
        selectedLine = this.currentOrder.get_selected_orderline();
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
                this.pos.data.syncDataWithIndexedDB(this.pos.data.records);
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
