/** @odoo-module */

import PaymentScreen from "@point_of_sale/js/Screens/PaymentScreen/PaymentScreen";
import Registries from "@point_of_sale/js/Registries";
const { onMounted } = owl;

const PosAdyenPaymentScreen = (PaymentScreen) =>
    class extends PaymentScreen {
        setup() {
            super.setup();
            onMounted(() => {
                const pendingPaymentLine = this.currentOrder.paymentlines.find(
                    (paymentLine) =>
                        paymentLine.payment_method.use_payment_terminal === "adyen" &&
                        !paymentLine.is_done() &&
                        paymentLine.get_payment_status() !== "pending"
                );
                if (pendingPaymentLine) {
                    const paymentTerminal = pendingPaymentLine.payment_method.payment_terminal;
                    paymentTerminal.set_most_recent_service_id(
                        pendingPaymentLine.terminalServiceId
                    );
                    pendingPaymentLine.set_payment_status("waiting");
                    paymentTerminal.start_get_status_polling().then((isPaymentSuccessful) => {
                        if (isPaymentSuccessful) {
                            pendingPaymentLine.set_payment_status("done");
                            pendingPaymentLine.can_be_reversed = paymentTerminal.supports_reversals;
                        } else {
                            pendingPaymentLine.set_payment_status("retry");
                        }
                    });
                }
            });
        }
    };

Registries.Component.extend(PaymentScreen, PosAdyenPaymentScreen);

export default PaymentScreen;
