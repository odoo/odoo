/** @odoo-module **/

import Registries from "@point_of_sale/js/Registries";
import PaymentScreen from "@point_of_sale/js/Screens/PaymentScreen/PaymentScreen";

export const PosSAPaymentScreen = PaymentScreen =>
    class extends PaymentScreen {
        //@Override
        toggleIsToInvoice() {
            // If the company is Saudi, POS orders should always be Invoiced
            if (this.currentOrder.pos.company.country && this.currentOrder.pos.company.country.code === 'SA') return false
            return super.toggleIsToInvoice(...arguments);
        }
    };

Registries.Component.extend(PaymentScreen, PosSAPaymentScreen);
