import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    async add_tyro_surcharge(amount, surchargeProduct) {
        const currentOrder = this.get_order();
        const line = currentOrder.lines.find((line) => line.product_id.id === surchargeProduct.id);

        if (line) {
            line.set_unit_price(amount + line.price_unit);
        } else {
            await this.addLineToCurrentOrder({
                product_id: surchargeProduct,
                price_unit: amount,
                product_tmpl_id: surchargeProduct.product_tmpl_id,
            });
        }
    },

    async onDeleteOrder(order) {
        if (order.get_total_paid() > 0) {
            this.dialog.add(AlertDialog, {
                title: _t("Cannot cancel order"),
                body: _t(
                    "This order has one or more completed payments, please refund them before cancelling."
                ),
            });
            return false;
        }
        return super.onDeleteOrder(...arguments);
    },

    onClickBackButton() {
        if (this.get_order()?.tyro_payment_in_progress()) {
            this.dialog.add(AlertDialog, {
                title: _t("Payment in progress"),
                body: _t("Please complete or cancel the payment before navigatating away."),
            });
        } else {
            return super.onClickBackButton(...arguments);
        }
    },
});
