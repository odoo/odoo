odoo.define('adyen_platforms.transactions', function (require) {
"use strict";

var ListController = require('web.ListController');
var ListView = require('web.ListView');
var viewRegistry = require('web.view_registry');

var TransactionsListController = ListController.extend({
    buttons_template: 'AdyenTransactionsListView.buttons',
    events: _.extend({}, ListController.prototype.events, {
        'click .o_button_sync_transactions': '_onTransactionsSync',
    }),

    _onTransactionsSync: function () {
        var self = this;
        this._rpc({
            model: 'adyen.transaction',
            method: 'sync_adyen_transactions',
            args: [],
        }).then(function () {
            self.trigger_up('reload');
        });
    }
});

var TransactionsListView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        Controller: TransactionsListController,
    }),
});

viewRegistry.add('adyen_transactions_tree', TransactionsListView);
});
