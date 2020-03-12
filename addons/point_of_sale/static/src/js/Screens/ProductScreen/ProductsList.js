odoo.define('point_of_sale.ProductsList', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');
    const { ProductDisplay } = require('point_of_sale.ProductDisplay');
    const Registry = require('point_of_sale.ComponentsRegistry');

    class ProductsList extends PosComponent {
        static template = 'ProductsList';
    }

    ProductsList.components = { ProductDisplay };

    Registry.add('ProductsList', ProductsList);

    return { ProductsList };
});
