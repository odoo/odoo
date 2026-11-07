/** @odoo-module */

import { PartnerListScreen } from "@point_of_sale/app/screens/partner_list/partner_list";
import { patch } from "@web/core/utils/patch";

patch(PartnerListScreen.prototype, {
    /**
     * Needs to be set to true to show the loyalty points in the partner list.
     * @override
     */
    get isBalanceDisplayed() {
        return true;
    },
});
