odoo.define('account.bills.tree', function (require) {
"use strict";
    var core = require('web.core');
    var ListController = require('web.ListController');
    var ListView = require('web.ListView');
    var viewRegistry = require('web.view_registry');

    var qweb = core.qweb;

    var BillsListController = ListController.extend({
        buttons_template: 'BillsListView.buttons',
        /**
         * Extends the renderButtons function of ListView by adding an event listener
         * on the bill upload button.
         *
         * @override
         */
        renderButtons: function () {
            this._super.apply(this, arguments); // Possibly sets this.$buttons
            if (this.$buttons) {
                var self = this;
                this.$buttons.on('click', '.o_button_upload_bill', function () {
                    var state = self.model.get(self.handle, {raw: true});
                    var context = state.getContext();
                    context['type'] = context.default_type || 'in_invoice';
                    self.do_action({
                        type: 'ir.actions.act_window',
                        res_model: 'account.invoice.import.wizard',
                        target: 'new',
                        views: [[false, 'form']],
                        context: context,
                    });
                });
            }
        }
    });

    var BillsListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: BillsListController,
        }),
    });

    viewRegistry.add('account_bills_tree', BillsListView);
});
