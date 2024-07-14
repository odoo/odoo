/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";


registry.category("web_tour.tours").add('account_accountant_batch_payment_bank_rec_widget',
    {
        test: true,
        url: '/web',
        steps: () => [
        stepUtils.showAppsMenuItem(),
        ...stepUtils.goToAppSteps('account_accountant.menu_accounting', "Open the accounting module"),

        // Open the widget. The first line should be selected by default.
        {
            content: "Open the bank reconciliation widget",
            extra_trigger: ".o_breadcrumb",
            trigger: "button.btn-primary[name='action_open_reconcile']",
        },
        {
            content: "The 'line1' should be selected by default",
            trigger: "div[name='line_ids'] td[field='name']:contains('line1')",
            run: function() {},
        },

        // Mount the batch payment and remove one payment.
        {
            content: "Click on the 'batch_payments_tab'",
            trigger: "a[name='batch_payments_tab']",
        },
        {
            content: "Mount BATCH0001",
            trigger: "div.bank_rec_widget_form_batch_payments_list_anchor table.o_list_table td[name='name']:contains('BATCH0001')",
        },
        {
            content: "Remove the payment of 100.0",
            extra_trigger: "div.bank_rec_widget_form_batch_payments_list_anchor table.o_list_table tr.o_rec_widget_list_selected_item",
            trigger: "div[name='line_ids'] .fa-trash-o:last",
        },

        // Check the batch rejection wizard.
        {
            content: "Validate and open the wizard",
            extra_trigger: "button.btn-primary:contains('Validate')",
            trigger: "button:contains('Validate')",
        },
        {
            content: "Click on 'Cancel'",
            extra_trigger: "div.modal-content",
            trigger: "div.modal-content button[name='button_cancel']",
        },
        {
            content: "Validate and open the wizard",
            extra_trigger: "body:not(.modal-open)",
            trigger: "button:contains('Validate')",
        },
        {
            content: "Click on 'Expect Payments Later'",
            extra_trigger: "div.modal-content",
            trigger: "div.modal-content button[name='button_continue']",
        },

        // Reconcile 'line2' with the remaining payment in batch.
        {
            content: "The 'line2' should be selected by default",
            extra_trigger: "div[name='line_ids'] td[field='name']:contains('line2')",
            trigger: "div[name='line_ids'] td[field='name']:contains('line2')",
            run: function() {},
        },
        {
            content: "Click on the 'batch_payments_tab'",
            trigger: "a[name='batch_payments_tab']",
        },
        {
            content: "Mount BATCH0001",
            trigger: "div.bank_rec_widget_form_batch_payments_list_anchor table.o_list_table td[name='name']:contains('BATCH0001')",
        },
        {
            content: "Validate. The wizard should be opened.",
            extra_trigger: "button.btn-primary:contains('Validate')",
            trigger: "button:contains('Validate')",
        },
        {
            content: "The 'line3' should be selected by default",
            extra_trigger: "div[name='line_ids'] td[field='name']:contains('line3')",
            trigger: "div[name='line_ids'] td[field='name']:contains('line3')",
            run: function() {},
        },
        stepUtils.toggleHomeMenu(),
        ...stepUtils.goToAppSteps(
            'account_accountant.menu_accounting',
            "Reset back to accounting module"
        ),
        {
            content: "check that we're back on the dashboard",
            trigger: 'a:contains("Customer Invoices")',
            run() {}
        }
    ]
});
