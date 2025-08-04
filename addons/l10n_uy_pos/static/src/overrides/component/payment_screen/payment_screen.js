import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    onMounted() {
        super.onMounted();
        if (this.pos.company.country_id?.code == "UY") {
            this.currentOrder.set_to_invoice(true);
        }
    },
});
