import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { DatePickerPopup } from "@pos_stock/app/components/popups/date_picker_popup/date_picker_popup";

patch(PaymentScreen.prototype, {
    async toggleShippingDatePicker() {
        if (!this.currentOrder.shipping_date) {
            this.dialog.add(DatePickerPopup, {
                title: _t("Select the shipping date"),
                getPayload: (shippingDate) => {
                    this.currentOrder.shipping_date = shippingDate;
                },
            });
        } else {
            this.currentOrder.shipping_date = false;
        }
    },
});
