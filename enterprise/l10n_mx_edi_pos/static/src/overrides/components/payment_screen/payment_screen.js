import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.isMxEdiPopupOpen = false;
    },
    //@override
    async toggleIsToInvoice() {
        if (this.pos.company.country_id?.code === "MX" && !this.currentOrder.is_to_invoice()) {
            const addedMxFields = await this.pos.addL10nMxEdiFields(this.currentOrder);
            if (!addedMxFields) {
                this.currentOrder.set_to_invoice(!this.currentOrder.is_to_invoice());
            }
        }
        super.toggleIsToInvoice(...arguments);
    },
    areMxFieldsVisible() {
        return this.pos.company.country_id?.code === "MX" && this.currentOrder.is_to_invoice();
    },
});
