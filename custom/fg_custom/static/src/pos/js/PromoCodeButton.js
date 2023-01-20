odoo.define('fg_custom.PromoCodeButton', function(require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');
    const PromoCodeButton = require('pos_coupon.PromoCodeButton');

    const FGPromoCodeButton = PromoCodeButton =>
        class extends PromoCodeButton {
            async onClick() {
                const currentClient = this.env.pos.get_order().get_client();
//                if (currentClient) {
//                }else{
//                    this.showPopup('ErrorPopup', {
//                        title: this.env._t("Set customer"),
//                        body: this.env._t("This order not available customer, first set custom"),
//                    });
//                    return;
//                }
                await super.onClick();
            }
        };

    Registries.Component.extend(PromoCodeButton, FGPromoCodeButton);
    return PromoCodeButton;
});
