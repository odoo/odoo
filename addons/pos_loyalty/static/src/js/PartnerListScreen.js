odoo.define('pos_loyalty.PartnerListScreen', function (require) {
    'use strict';

    const PartnerListScreen = require('point_of_sale.PartnerListScreen');
    const Registries = require('point_of_sale.Registries');

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

    return PartnerListScreen;
});
