/** @odoo-module */

import { PartnerListScreen } from "@point_of_sale/js/Screens/PartnerListScreen/PartnerListScreen";
import { patch } from "@web/core/utils/patch";

patch(PartnerListScreen.prototype, "pos_loyalty.PartnerListScreen", {
    /**
     * Needs to be set to true to show the loyalty points in the partner list.
     * @override
     */
    get isBalanceDisplayed() {
        return true;
    },
});
