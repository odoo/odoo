/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { BillScreen } from "@pos_restaurant/app/bill_screen/bill_screen";

patch(BillScreen.prototype, {
    // We don't want the content of onWillStart from the receipt screen to be executed
    // because it would send the command to the kitchen
    async sendOrderToPreparationTools() {},
});
