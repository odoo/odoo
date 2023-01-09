/** @odoo-module */

import PartnerListScreen from "@point_of_sale/js/Screens/PartnerListScreen/PartnerListScreen";
import Registries from "@point_of_sale/js/Registries";

const PosLoyaltyPartnerListScreen = (PartnerListScreen) =>
    class extends PartnerListScreen {
        /**
         * Needs to be set to true to show the loyalty points in the partner list.
         * @override
         */
        get isBalanceDisplayed() {
            return true;
        }
    };

Registries.Component.extend(PartnerListScreen, PosLoyaltyPartnerListScreen);

export default PartnerListScreen;
