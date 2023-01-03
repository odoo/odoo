/** @odoo-module */

import PaymentScreenPaymentLines from "@point_of_sale/js/Screens/PaymentScreen/PaymentScreenPaymentLines";
import Registries from "@point_of_sale/js/Registries";

const PosMercuryPaymentLines = (PaymentScreenPaymentLines) =>
    class extends PaymentScreenPaymentLines {
        /**
         * @override
         */
        selectedLineClass(line) {
            return Object.assign({}, super.selectedLineClass(line), {
                o_pos_mercury_swipe_pending: line.mercury_swipe_pending,
            });
        }
        /**
         * @override
         */
        unselectedLineClass(line) {
            return Object.assign({}, super.unselectedLineClass(line), {
                o_pos_mercury_swipe_pending: line.mercury_swipe_pending,
            });
        }
    };

Registries.Component.extend(PaymentScreenPaymentLines, PosMercuryPaymentLines);

export default PaymentScreenPaymentLines;
