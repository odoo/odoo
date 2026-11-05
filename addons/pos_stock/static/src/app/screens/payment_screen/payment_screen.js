import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { DatePickerPopup } from "@pos_stock/app/components/popups/date_picker_popup/date_picker_popup";

patch(PaymentScreen.prototype, {
    async toggleShippingDatePicker() {
        this.dialog.add(DatePickerPopup, {
            title: _t("Schedule for later"),
            defaultValue: this.currentOrder.shipping_date,
            defaultType: this.currentOrder.pickup_later ? "pickup" : "ship",
            getPayload: (shippingDate, scheduleType) => {
                this.currentOrder.shipping_date = shippingDate;
                this.currentOrder.pickup_later = scheduleType === "pickup";
            },
        });
    },

    shouldShowTipOrder() {
        return super.shouldShowTipOrder() || this.pos.config.ship_later;
    },

    optionalButtonValues() {
        return super.optionalButtonValues() || this.pos.config.ship_later;
    },
});
