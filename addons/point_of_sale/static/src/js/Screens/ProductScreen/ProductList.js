odoo.define('point_of_sale.ProductList', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class ProductList extends PosComponent {}
    ProductList.template = 'ProductList';

    Registries.Component.add(ProductList);

    return ProductList;
});
