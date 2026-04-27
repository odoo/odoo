/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import { accountTourSteps } from "@account/js/tours/account";


registry.category("web_tour.tours").add('account_accountant_bank_rec_widget_save_analytic_distribution', {
    url: '/odoo',
    steps: () => [
        stepUtils.showAppsMenuItem(),
        ...accountTourSteps.goToAccountMenu("Open the accounting module"),
        {
            trigger: ".o_breadcrumb",
        },
        {
            content: "Open the bank reconciliation widget",
            trigger: "button.btn-secondary[name='action_open_reconcile']",
            run: "click",
        },
        {
            trigger: "div[name='line_ids']",
        },
        {
            content: "The 'line1' should be selected by default",
            trigger: "div[name='line_ids'] td[field='name']:contains('line1')",
            run: function() {},
        },
        {
            content: "Click on first line",
            trigger: "div[name='line_ids'] td[field='debit']:first",
            run: "click",
        },
        {
            content: "The 'manual_operations_tab' should be active now and the auto_balance line mounted in edit",
            trigger: "a.active[name='manual_operations_tab']",
            run: function() {},
        },
        {
            content: "Enter an analytic distribution",
            trigger: "div[name='analytic_distribution'] .o_input_dropdown",
            run: "click",
        },
        {
            content: "Select analytic distribution",
            trigger: "tr[name='line_0'] input",
            run: "edit analytic_account",
        },
        {
            trigger: ".ui-autocomplete",
        },
        {
            content: "Select analytic distribution",
            trigger: ".ui-autocomplete:visible li:contains('analytic_account')",
            run: "click",
        },
        {
            content: "Close the analytic distribution",
            trigger: ".o_button",
            run: "click",
        },
        ...stepUtils.toggleHomeMenu(),
        ...accountTourSteps.goToAccountMenu("Reset back to accounting module"),
        {
            content: "check that we're back on the dashboard",
            trigger: 'a:contains("Customer Invoices")',
        },
    ]
});
