odoo.define('l10n_de_pos_cert.ProductScreen', function(require) {
    "use strict";

    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');
/*
    useless for now, only worth it for restaurant because we don't store the unpaid order in the database
    meaning that it will be possible to create a transaction and never finishing/canceling it
*/
    const _super_productscreen = ProductScreen.prototype;

    const PosDeProductScreen = ProductScreen => class extends ProductScreen {
        async _clickProduct(event) {
            _super_productscreen._clickProduct.apply(this,arguments);
            if (!this.currentOrder.isTransactionStarted()) {
//                this.currentOrder.startTransaction();
            }
        }
    }

    Registries.Component.extend(ProductScreen, PosDeProductScreen);

    return PosDeProductScreen;
});

