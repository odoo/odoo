/** @odoo-module */

import PaymentScreen from "@point_of_sale/js/Screens/PaymentScreen/PaymentScreen";
import { useListener } from "@web/core/utils/hooks";
import Registries from "@point_of_sale/js/Registries";

const PosResPaymentScreen = (PaymentScreen) =>
    class extends PaymentScreen {
        setup() {
            super.setup();
            useListener("send-payment-adjust", this._sendPaymentAdjust);
        }

        async _sendPaymentAdjust({ detail: line }) {
            const previous_amount = line.get_amount();
            const amount_diff = line.order.get_total_with_tax() - line.order.get_total_paid();
            line.set_amount(previous_amount + amount_diff);
            line.set_payment_status("waiting");

            const payment_terminal = line.payment_method.payment_terminal;
            const isAdjustSuccessful = await payment_terminal.send_payment_adjust(line.cid);
            if (isAdjustSuccessful) {
                line.set_payment_status("done");
            } else {
                line.set_amount(previous_amount);
                line.set_payment_status("done");
            }
        }

        get nextScreen() {
            const order = this.currentOrder;
            if (!this.env.pos.config.set_tip_after_payment || order.is_tipped) {
                return super.nextScreen;
            }
            // Take the first payment method as the main payment.
            const mainPayment = order.get_paymentlines()[0];
            if (mainPayment.canBeAdjusted()) {
                return "TipScreen";
            }
            return super.nextScreen;
        }
    };

Registries.Component.extend(PaymentScreen, PosResPaymentScreen);

export default PosResPaymentScreen;
