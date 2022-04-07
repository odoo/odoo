odoo.define('sale.SaleOrderView', function (require) {
    "use strict";

    const SaleOrderFormController = require('sale.SaleOrderFormController');
    const FormView = require('web.FormView');
    const viewRegistry = require('web.view_registry');

    const SaleOrderView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Controller: SaleOrderFormController,
        }),
    });

    viewRegistry.add('sale_discount_form', SaleOrderView);

    return SaleOrderView;

});
