odoo.define('flexipharmacy.ProductsWidget', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductsWidget = require('point_of_sale.ProductsWidget');
    const { Gui } = require('point_of_sale.Gui');
    const { useListener } = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');
    const { useRef, useState } = owl.hooks;
    var rpc = require('web.rpc');

    const AsplRetProductsWidgetInh = (ProductsWidget) =>
        class extends ProductsWidget {
            constructor(){
                super(...arguments);
                useListener('click-product-category', this.OpenProductCategory);
            }
            OpenProductCategory(){
                this.state.expanded = !this.state.expanded
            }
        }

    Registries.Component.extend(ProductsWidget, AsplRetProductsWidgetInh);

    return ProductsWidget;

});
