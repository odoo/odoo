odoo.define('point_of_sale.ProductsList', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');
    const { ProductDisplay } = require('point_of_sale.ProductDisplay');

    class ProductsList extends PosComponent {}

    ProductsList.components = { ProductDisplay };

    return { ProductsList };
});
