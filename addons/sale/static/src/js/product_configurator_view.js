odoo.define('sale.ProductConfiguratorFormView', function (require) {
"use strict";

var ProductConfiguratorFormController = require('sale.ProductConfiguratorFormController');
var ProductConfiguratorFormRenderer = require('sale.ProductConfiguratorFormRenderer');
var FormView = require('web.FormView');
var viewRegistry = require('web.view_registry');

var ProductConfiguratorFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller: ProductConfiguratorFormController,
        Renderer: ProductConfiguratorFormRenderer,
    }),
});

viewRegistry.add('product_configurator_form', ProductConfiguratorFormView);

return ProductConfiguratorFormView;

});