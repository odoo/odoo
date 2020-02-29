odoo.define('stock.InventoryValidationView', function (require) {
"use strict";

var InventoryValidationController = require('stock.InventoryValidationController');
var ListView = require('web.ListView');
var viewRegistry = require('web.view_registry');

var InventoryValidationView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        Controller: InventoryValidationController
    })
});

viewRegistry.add('inventory_validate_button', InventoryValidationView);

});
