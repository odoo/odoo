odoo.define('stock.SingletonListView', function (require) {
'use strict';

var ListView = require('web.ListView');
var SingletonListController = require('stock.SingletonListController');
var viewRegistry = require('web.view_registry');

var SingletonListView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        Controller: SingletonListController,
    }),
});

viewRegistry.add('singleton_list', SingletonListView);

return SingletonListView;

});
