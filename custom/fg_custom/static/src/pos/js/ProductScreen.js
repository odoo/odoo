odoo.define('fg_custom.ProductScreen', function(require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');
    const ProductScreen = require('point_of_sale.ProductScreen');

    const FGProductScreen = ProductScreen =>
        class extends ProductScreen {
            async _onClickPay() {
                const currentClient = this.env.pos.get_order().get_client();
                if (currentClient) {
                }else{
                    this.showPopup('ErrorPopup', {
                        title: this.env._t("Set customer"),
                        body: this.env._t("This order not available customer, first set custom"),
                    });
                    return;
                }
                await super._onClickPay();
            }
        };

    Registries.Component.extend(ProductScreen, FGProductScreen);
    return ProductScreen;
});
