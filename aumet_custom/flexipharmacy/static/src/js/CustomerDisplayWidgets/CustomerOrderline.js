odoo.define('flexipharmacy.CustomerOrderline', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class CustomerOrderline extends PosComponent {}
    CustomerOrderline.template = 'CustomerOrderline';

    Registries.Component.add(CustomerOrderline);

    return CustomerOrderline;
});
