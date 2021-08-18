odoo.define('flexipharmacy.ProductSummaryReceipt', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class ProductSummaryReceipt extends PosComponent {}
    ProductSummaryReceipt.template = 'ProductSummaryReceipt';

    Registries.Component.add(ProductSummaryReceipt);

    return ProductSummaryReceipt;
});
