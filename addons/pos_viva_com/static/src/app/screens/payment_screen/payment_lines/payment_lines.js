import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";
import { patch } from "@web/core/utils/patch";
import { useVivaApp } from "../../../hooks/use_viva_app";

patch(PaymentScreenPaymentLines.prototype, {
    setup() {
        super.setup();
        this.vivaApp = useVivaApp();
    },
});
