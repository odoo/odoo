odoo.define('stock.SingletonListView', function (require) {
'use strict';

var InventoryReportListView = require('stock.InventoryReportListView');
var SingletonListController = require('stock.SingletonListController');
var SingletonListRenderer = require('stock.SingletonListRenderer');
var viewRegistry = require('web.view_registry');

var SingletonListView = InventoryReportListView.extend({
    config: _.extend({}, InventoryReportListView.prototype.config, {
        Controller: SingletonListController,
        Renderer: SingletonListRenderer,
    }),
});

viewRegistry.add('singleton_list', SingletonListView);

return SingletonListView;

});
