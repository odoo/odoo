odoo.define('adyen_platforms.transactions.dashboard', function (require) {
    "use strict";

    var ListRenderer = require('web.ListRenderer');
    var ListView = require('web.ListView');

    var viewRegistry = require('web.view_registry');

    var core = require('web.core');
    var QWeb = core.qweb;

    var AdyenTransactionsListRenderer = ListRenderer.extend({
        _render: function () {
            const el = this.$el.parent();
            return this._super.apply(this, arguments).then(() => {
                this._rpc({
                    model: 'adyen.account.balance',
                    method: 'get_account_balance',
                    content: this.context
                }).then((result) => {
                    el.parent().find('.o_adyen_transactions_dashboard').remove();

                    const dash = QWeb.render('AdyenTransactions.dashboard', { 
                        balances: result,
                    });
                    el.before(dash);
                });
            });
        }
    });

    var AdyenTransactionsListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Renderer: AdyenTransactionsListRenderer
        }),
    });

    viewRegistry.add('adyen_transactions_list', AdyenTransactionsListView);
});
