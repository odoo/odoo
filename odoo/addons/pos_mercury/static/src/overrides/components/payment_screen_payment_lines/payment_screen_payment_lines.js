/** @odoo-module */

import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreenPaymentLines.prototype, {
    /**
     * @override
     */
    selectedLineClass(line) {
        return Object.assign({}, super.selectedLineClass(line), {
            o_pos_mercury_swipe_pending: line.mercury_swipe_pending,
        });
    },
    /**
     * @override
     */
    unselectedLineClass(line) {
        return Object.assign({}, super.unselectedLineClass(line), {
            o_pos_mercury_swipe_pending: line.mercury_swipe_pending,
        });
    },
});
