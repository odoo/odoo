/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(PaymentScreen.prototype, {
    //@override
    async validateOrder(isForceValidate) { // todo take into account when validation of order failed, what to do ?
        return await super.validateOrder(...arguments);
    }

    /**
     * @override
     */
    // async _postPushOrderResolve(order, server_ids) {
    // }
});
