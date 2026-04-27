/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import { accountTourSteps } from "@account/js/tours/account";

registry.category("web_tour.tours").add("account_accountant_bank_rec_widget", {
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
            trigger: "div[name='line_ids']",
        },
        {
            content: "The 'line1' should be selected by default",
            trigger: "div[name='line_ids'] td[field='name']:contains('line1')",
        },

        // Test 1: Check the loading of lazy notebook tabs.
        // Check 'amls_tab' (active by default).
        {
            trigger: "div.bank_rec_widget_form_amls_list_anchor table.o_list_table",
        },
        {
            content: "The 'amls_tab' should be active and the inner list view loaded",
            trigger: "a.active[name='amls_tab']",
        },
        // Check 'discuss_tab'.
        {
            trigger: "a.active[name='amls_tab']",
        },
        {
            content: "Click on the 'discuss_tab'",
            trigger: "a[name='discuss_tab']",
            run: "click",
        },
        {
            trigger: "a.active[name='discuss_tab']",
        },
        {
            content: "The 'discuss_tab' should be active and the chatter loaded",
            trigger: "div.bank_rec_widget_form_discuss_anchor div.o-mail-Chatter",
        },
        // Check 'manual_operations_tab'.
        {
            trigger: "tr.o_bank_rec_auto_balance_line",
        },
        {
            content: "Click on the 'auto_balance' to make the 'manual_operations_tab' visible",
            trigger: "tr.o_bank_rec_auto_balance_line td[field='name']",
            run: "click",
        },
        {
            content: "The 'manual_operations_tab' should be active",
            trigger: "a.active[name='manual_operations_tab']",
        },
        {
            content: "The 'name' field should be focus automatically",
            trigger: "div.o_notebook div[name='name'] input:focus",
        },
        {
            trigger: "tr.o_bank_rec_auto_balance_line",
        },
        {
            content: "Click on the 'credit' field to change the focus from 'name' to 'amount_currency'",
            trigger: "tr.o_bank_rec_auto_balance_line td[field='credit']",
            run: "click",
        },
        {
            content: "Wait to avoid non-deterministic errors on the next step",
            trigger: "tr.o_bank_rec_auto_balance_line td[field='credit']",
        },
        {
            content: "The 'balance' field should be focus now",
            trigger: "div.o_notebook div[name='amount_currency'] input:focus",
        },

        // Test 2: Test validation + auto select the next line.
        {
            trigger: "a.active[name='manual_operations_tab']",
        },
        {
            content: "Click on the 'amls_tab'",
            trigger: "a[name='amls_tab']",
            run: "click",
        },
        {
            trigger: "a.active[name='amls_tab']",
        },
        {
            content: "Mount INV/2019/00002",
            trigger:
                "div.bank_rec_widget_form_amls_list_anchor table.o_list_table td[name='move_id']:contains('INV/2019/00002')",
            run: "click",
        },
        {
            trigger:
                "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr.o_rec_widget_list_selected_item td[name='move_id']:contains('INV/2019/00002')",
        },
        {
            content: "Check INV/2019/00002 is well marked as selected",
            trigger:
                "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr.o_rec_widget_list_selected_item td[name='move_id']:contains('INV/2019/00002')",
        },
        {
            trigger:
                "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr.o_rec_widget_list_selected_item td[name='move_id']:contains('INV/2019/00002')",
        },
        {
            content: "Remove INV/2019/00002",
            trigger: "tr td.o_list_record_remove button",
            run: "click",
        },
        {
            trigger:
                "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr:not(.o_rec_widget_list_selected_item) td[name='move_id']:contains('INV/2019/00002')",
        },
        {
            content: "Mount INV/2019/00001",
            trigger:
                "div.bank_rec_widget_form_amls_list_anchor table.o_list_table td[name='move_id']:contains('INV/2019/00001')",
            run: "click",
        },
        {
            trigger:
                "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr.o_rec_widget_list_selected_item td[name='move_id']:contains('INV/2019/00001')",
        },
        {
            content: "Validate",
            trigger: "button:contains('Validate')",
            run: "click",
        },
        {
            trigger: "div[name='line_ids'] td[field='name']:contains('line2')",
        },
        {
            content: "The 'line2' is the next not already reconciled line",
            trigger: "div[name='line_ids'] td[field='name']:contains('line2')",
        },

        // Test 3: Test manual operations tab.
        {
            content: "Click on 'credit'",
            trigger: "div[name='line_ids'] td[field='credit']:last",
            run: "click",
        },
        {
            content:
                "The 'manual_operations_tab' should be active now and the auto_balance line mounted in edit",
            trigger: "a.active[name='manual_operations_tab']",
        },
        {
            content: "The last line should be selected",
            trigger: "div[name='line_ids'] tr.o_bank_rec_selected_line",
        },
        {
            content: "Search for 'partner_a'",
            trigger: "div[name='partner_id'] input",
            run: "edit partner_a",
        },
        {
            trigger: ".ui-autocomplete .o_m2o_dropdown_option a:contains('Create')",
        },
        {
            content: "Select 'partner_a'",
            trigger: ".ui-autocomplete:visible li:contains('partner_a')",
            run: "click",
        },
        {
            trigger:
                "tr:not(.o_bank_rec_auto_balance_line) td[field='partner_id']:contains('partner_a')",
        },
        {
            content: "Select the payable account",
            trigger: "button:contains('Payable')",
            run: "click",
        },
        {
            trigger:
                "tr:not(.o_bank_rec_auto_balance_line) td[field='account_id']:contains('Payable')",
        },
        {
            content: "Enter a tax",
            trigger: "div[name='tax_ids'] input",
            run: "edit 15",
        },
        {
            trigger: ".ui-autocomplete",
        },
        {
            content: "Select 'Tax 15% (Sales)'",
            trigger: ".ui-autocomplete:visible li:contains('Sales')",
            run: "click",
        },
        {
            content: "Tax column appears in list of lines",
            trigger: "div[name='line_ids'] td[field='tax_ids']",
        },
        {
            content: "Wait to avoid non-deterministic errors on the next step",
            trigger: "div[name='line_ids'] td:contains('Tax Received')",
        },
        {
            trigger: "button.btn-primary:contains('Validate')",
        },
        {
            content: "Validate",
            trigger: "button:contains('Validate')",
            run: "click",
        },
        {
            trigger: "div[name='line_ids'] td[field='name']:contains('line3')",
        },
        {
            content: "The 'line3' is the next not already reconciled line",
            trigger: "div[name='line_ids'] td[field='name']:contains('line3')",
        },
        ...stepUtils.toggleHomeMenu(),
        ...accountTourSteps.goToAccountMenu("Reset back to accounting module"),
        {
            content: "check that we're back on the dashboard",
            trigger: 'a:contains("Customer Invoices")',
        },
    ],
});
