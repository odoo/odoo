odoo.define('hr_payroll.payslip.tree', function (require) {
"use strict";
    var core = require('web.core');
    var ListController = require('web.ListController');
    var ListView = require('web.ListView');
    var viewRegistry = require('web.view_registry');

    var QWeb = core.qweb;

    var PayslipListController = ListController.extend({
        /**
         * Extends the renderButtons function of ListView by adding a button
         * on the payslip list.
         *
         * @override
         */
        renderButtons: function () {
            this._super.apply(this, arguments);
            this.$buttons.append($(QWeb.render("PayslipListView.print_button", this)));
            var self = this;
            this.$buttons.on('click', '.o_button_print_payslip', function () {
                if (self.getSelectedIds().length == 0) {
                    return;
                }
                return self._rpc({
                    model: 'hr.payslip',
                    method: 'action_print_payslip',
                    args: [self.getSelectedIds()],
                }).then(function (results) {
                    self.do_action(results);
                });
            });
        }
    });

    var PayslipListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: PayslipListController,
        }),
    });

    viewRegistry.add('hr_payroll_payslip_tree', PayslipListView);
});
