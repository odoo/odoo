odoo.define('stock.StockOrderpointListView', function (require) {
"use strict";

var ListView = require('web.ListView');
var StockOrderpointListController = require('stock.StockOrderpointListController');
var StockOrderpointListModel = require('stock.StockOrderpointListModel');
var StockOrderpointListRenderer = require('stock.StockOrderpointListRenderer');
var viewRegistry = require('web.view_registry');


var StockOrderpointListView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        Controller: StockOrderpointListController,
        Model: StockOrderpointListModel,
        Renderer: StockOrderpointListRenderer,
    }),
});

viewRegistry.add('stock_orderpoint_list', StockOrderpointListView);

return StockOrderpointListView;

});
