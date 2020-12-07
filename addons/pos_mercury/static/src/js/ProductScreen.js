odoo.define('pos_mercury.ProductScreen', function (require) {
    'use strict';

    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useBarcodeReader } = require('point_of_sale.custom_hooks');
    const { patch } = require('web.utils');

    patch(ProductScreen.prototype, 'pos_mercury', {
        setup() {
            this._super(...arguments);
            useBarcodeReader(this.env.model.barcodeReader, {
                credit: this._onCardSwipe,
            });
        },
        _onCardSwipe() {
            this.env.ui.askUser('ErrorPopup', {
                body: this.env._t('Go to payment screen to use cards'),
            });
        },
    });

    return ProductScreen;
});
