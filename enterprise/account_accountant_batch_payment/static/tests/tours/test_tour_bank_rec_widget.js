/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import { accountTourSteps } from "@account/js/tours/account";

registry.category("web_tour.tours").add("account_accountant_batch_payment_bank_rec_widget", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        ...accountTourSteps.goToAccountMenu("Open the accounting module"),

        // Open the widget. The first line should be selected by default.
        {
            trigger: ".o_breadcrumb",
        },
        {
            content: "Open the bank reconciliation widget",
            trigger: "button.btn-secondary[name='action_open_reconcile']",
            run: "click",
        },
        {
            content: "The 'line1' should be selected by default",
            trigger: "div[name='line_ids'] td[field='name']:contains('line1')",
        },

        // Mount the batch payment and remove one payment.
        {
            content: "Click on the 'batch_payments_tab'",
            trigger: "a[name='batch_payments_tab']",
            run: "click",
        },
        {
            content: "Mount BATCH0001",
            trigger:
                "div.bank_rec_widget_form_batch_payments_list_anchor table.o_list_table td[name='name']:contains('BATCH0001')",
            run: "click",
        },
        {
            content: "The batch should be selected",
            trigger:
                "div.bank_rec_widget_form_batch_payments_list_anchor table.o_list_table tr.o_rec_widget_list_selected_item",
        },
        {
            content: "Open the batch",
            trigger: "div[name='line_ids'] .o_bank_rec_second_line .o_form_uri",
            run: "click",
        },
        {
            content: "Open the payment of 100.0",
            trigger: "div[name='payment_ids'] tbody tr.o_data_row:last .o_list_record_open_form_view button",
            run: "click",
        },
        {
            content: "Reject it",
            trigger: "button[name='action_reject']",
            run: "click",
        },
        {
            content: "Go back to the reconciliation widget",
            trigger: "a[href$='/reconciliation']",
            run: "click",
        },
        {
            trigger: "div[name='line_ids'] td[field='name']:contains('line1')",
        },
        {
            trigger: "button.btn-primary:contains('Validate')",
        },
        {
            content: "Validate",
            trigger: "button:contains('Validate')",
            run: "click",
        },
        ...stepUtils.toggleHomeMenu(),
        ...accountTourSteps.goToAccountMenu("Reset back to accounting module"),
        {
            content: "check that we're back on the dashboard",
            trigger: 'a:contains("Customer Invoices")',
        },
    ],
});

registry.category("web_tour.tours").add("account_accountant_batch_payment_bank_rec_widget_batch_line_clickable", {
    url: "/odoo",
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
            content: "Click on the 'batch_payments_tab'",
            trigger: "a[name='batch_payments_tab']",
            run: "click",
        },
        {
            content: "Mount BATCH0001",
            trigger: "div.bank_rec_widget_form_batch_payments_list_anchor table.o_list_table td[name='name']:contains('BATCH0001')",
            run: "click",
        },
        {
            content: "The batch should be selected",
            trigger: "div.bank_rec_widget_form_batch_payments_list_anchor table.o_list_table tr.o_rec_widget_list_selected_item",
        },
        {
            content: "Click batch row for BATCH0001",
            trigger: ".o_data_row.o_selected_row.o_list_no_open.o_bank_rec_second_line:contains('BATCH0001')",
            run: "click",
        },
        {
            content: "Wait for Manual Operations tab to open",
            trigger: "div[name='analytic_distribution']:not(:visible)",
        },
    ],
});
