odoo.define('flexipharmacy.AlternateProductScreen', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const { useListener } = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');
    var rpc = require('web.rpc');
    const { useState } = owl.hooks;

    class AlternateProductScreen extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click-alternate-product', this._clickAlternateProduct);
        }
        async _clickAlternateProduct(event){
            var self = this;
            var selectedOrder = this.env.pos.get_order();
            var selectedLine = self.env.pos.get_order().get_selected_orderline();
            selectedOrder.remove_orderline(selectedLine);
            const product = event.detail;
            selectedOrder.add_product(product, {
                name: product.display_name,
                price: product.lst_price,
            });
        }
    }

    AlternateProductScreen.template = 'AlternateProductScreen';

    Registries.Component.add(AlternateProductScreen);

    return AlternateProductScreen;
});
