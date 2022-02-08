odoo.define('pos_mercury.ProductScreen', function (require) {
    'use strict';

    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');
    const { useBarcodeReader } = require('point_of_sale.custom_hooks');

    const PosMercuryProductScreen = (ProductScreen) =>
        class extends ProductScreen {
            constructor() {
                super(...arguments);
                useBarcodeReader({
                    credit: this.credit_error_action,
                });
            }
            credit_error_action() {
                this.showPopup('ErrorPopup', {
                    body: this.env._t('Go to payment screen to use cards'),
                });
            }
        };

    Registries.Component.extend(ProductScreen, PosMercuryProductScreen);

    return ProductScreen;
});
