odoo.define('pos_sale.ProductScreen', function (require) {
    'use strict';

    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');

    const PosSaleProductScreen = (ProductScreen) =>
        class extends ProductScreen {
            async _newOrderlineSelected() {
                await super._newOrderlineSelected();
                this._setNumpadModeToPrice();
            }
            mounted() {
                super.mounted();
                this._setNumpadModeToPrice();
            }
            _setNumpadModeToPrice() {
                if (this.currentOrder) {
                    const selectedOrderline = this.currentOrder.get_selected_orderline();
                    if (selectedOrderline && selectedOrderline.product.id === selectedOrderline.pos.config.down_payment_product_id[0]) {
                        this.state.numpadMode = 'price';
                    }
                }
            }
        };

    Registries.Component.extend(ProductScreen, PosSaleProductScreen);

    return ProductScreen;
});
