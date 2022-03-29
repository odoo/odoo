odoo.define('account.chart.tree.import', function (require) {
    "use strict";
    var ListController = require('web.ListController');
    var ListView = require('web.ListView');

    var viewRegistry = require('web.view_registry');

    var AccountsListController = ListController.extend({
        buttons_template: 'AccountListView.buttons',
        events: _.extend({}, ListController.prototype.events, {
            'click .o_button_import_chart': '_importAccountAction',
        }),
        _importAccountAction: function(e) {
            this.do_action('base_import_account.account_import_action');
        }
    });

    var AccountsListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: AccountsListController,
        }),
    });

    viewRegistry.add('accountchart_tree_import', AccountsListView);
});
