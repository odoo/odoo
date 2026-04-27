/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import { patch } from "@web/core/utils/patch";
import { accountTourSteps } from "@account/js/tours/account";

patch(accountTourSteps, {
    bankRecUiReportSteps() {
        return [
            {
                trigger: ".o_bank_rec_selected_st_line:contains('line1')",
            },
            {
                content: "balance is 2100",
                trigger: ".btn-link:contains('$ 2,100.00')",
            },
        ];
    },
});

registry.category("web_tour.tours").add("account_accountant_bank_rec_widget_ui", {
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
            trigger: "div[name='line_ids'] td[field='name']:contains('line1')",
        },
        {
            content: "'line1' should be selected and form mounted",
            trigger: ".o_bank_rec_selected_st_line:contains('line1')",
        },
        // Select line2. It should remain selected when returning using the breadcrumbs.
        {
            trigger: ".o_bank_rec_st_line:contains('line3')",
        },
        {
            content: "select 'line2'",
            trigger: ".o_bank_rec_st_line:contains('line2')",
            run: "click",
        },
        {
            content: "'line2' should be selected",
            trigger: ".o_bank_rec_selected_st_line:contains('line2')",
        },
        {
            content: "View an invoice",
            trigger: "button.btn-secondary[name='action_open_business_doc']:eq(1)",
            run: "click",
        },
        {
            trigger: ".o_breadcrumb .active:contains('INV/2019/00001')",
        },
        {
            content: "Breadcrumb back to Bank Reconciliation from INV/2019/00001",
            trigger: ".breadcrumb-item:contains('Bank Reconciliation')",
            run: "click",
        },
        {
            trigger: ".o_bank_rec_st_line:contains('line1')",
        },
        {
            content: "'line2' should be selected after returning",
            trigger: ".o_bank_rec_selected_st_line:contains('line2')",
            run: "click",
        },
        {
            trigger: "div[name='line_ids'] td[field='name']:contains('line2')",
        },
        {
            content: "'line2' form mounted",
            trigger: ".o_bank_rec_selected_st_line:contains('line2')",
            run: "click",
        },
        // Keep AML search, and prepared entry (line_ids) when changing tabs, using breadcrumbs, and view switcher
        {
            trigger:
                "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr:nth-child(2) td[name='move_id']:contains('INV/2019/00001')",
        },
        {
            content: "AMLs list has both invoices",
            trigger:
                "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr:nth-child(1) td[name='move_id']:contains('INV/2019/00002')",
        },
        {
            trigger: "a.active[name='amls_tab']",
        },
        {
            content: "Search for INV/2019/00001",
            trigger: "div.bank_rec_widget_form_amls_list_anchor .o_searchview_input",
            run: "edit INV/2019/00001",
        },
        {
            content: "Select the Journal Entry search option from the dropdown",
            trigger: ".o_searchview_autocomplete li:contains(Journal Entry)",
            run: "click",
        },
        {
            content: "AMLs list only displays one invoice",
            trigger:
                "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr:nth-child(1) td[name='move_id']:contains('INV/2019/00001')",
        },
        {
            content: "Liquidity line displays debit '$ 1,000.00'",
            trigger:
                "div[name='line_ids'] table.o_list_table tr.o_bank_rec_liquidity_line td[field='debit']:contains('$ 1,000.00')",
        },
        {
            content: "Select the liquidity line",
            trigger: "tr.o_bank_rec_liquidity_line td[field='debit']",
            run: "click",
        },
        {
            content: "Modify the liquidity line amount",
            trigger: "div[name='amount_currency'] input",
            run: "edit 100.00 && click body",
        },
        {
            content: "Liquidity line displays debit '$ 100.00'",
            trigger:
                "div[name='line_ids'] table.o_list_table tr.o_bank_rec_liquidity_line td[field='debit']:contains('$ 100.00')",
        },
        {
            trigger: "div[name='partner_id'] input",
        },
        {
            content: "Select 'amls_tab'",
            trigger: "a[name='amls_tab']",
            run: "click",
        },
        {
            trigger:
                "div.bank_rec_widget_form_amls_list_anchor .o_searchview_facet:nth-child(1) .o_facet_value:contains('INV/2019/00001')",
        },
        {
            content: "AMLs list contains the search facet, and one invoice - select it",
            trigger:
                "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr:nth-child(1) td[name='move_id']:contains('INV/2019/00001')",
            run: "click",
        },
        {
            trigger:
                "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr.o_rec_widget_list_selected_item td[name='move_id']:contains('INV/2019/00001')",
        },
        {
            content: "Check INV/2019/00001 is well marked as selected",
            trigger:
                "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr.o_rec_widget_list_selected_item td[name='move_id']:contains('INV/2019/00001')",
        },
        {
            content: "View an invoice",
            trigger: "button.btn-secondary[name='action_open_business_doc']:nth-child(1)",
            run: "click",
        },
        {
            trigger: ".o_breadcrumb .active:contains('INV/2019/00001')",
        },
        {
            content: "Breadcrumb back to Bank Reconciliation from INV/2019/00001",
            trigger: ".breadcrumb-item:contains('Bank Reconciliation')",
            run: "click",
        },
        {
            trigger:
                "div.bank_rec_widget_form_amls_list_anchor .o_searchview_facet:nth-child(1) .o_facet_value:contains('INV/2019/00001')",
        },
        {
            content: "Check INV/2019/00001 is selected and still contains the search facet",
            trigger:
                "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr.o_rec_widget_list_selected_item td[name='move_id']:contains('INV/2019/00001')",
        },
        // Search should remove some lines, select the first unmatched record, and persist when returning with breadcrumbs
        {
            trigger: "a.active[name='amls_tab']",
        },
        {
            content: "Search for line2",
            trigger: "div.o_kanban_view .o_searchview_input",
            run: "fill line2",
        },
        {
            content: "Select the Transaction search option from the dropdown",
            trigger: ".o_searchview_autocomplete li:contains(Transaction)",
            run: "click",
        },
        {
            trigger: "div[name='line_ids'] td[field='name']:contains('line2')",
        },
        {
            content: "'line2' should be selected",
            trigger: ".o_bank_rec_st_line:last():contains('line2')",
        },
        {
            trigger:
                "div.bank_rec_widget_form_amls_list_anchor .o_searchview_facet:nth-child(1) .o_facet_value:contains('INV/2019/00001')",
        },
        {
            content:
                "Nothing has changed: INV/2019/00001 is selected and still contains the search facet",
            trigger:
                "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr.o_rec_widget_list_selected_item td[name='move_id']:contains('INV/2019/00001')",
        },
        {
            trigger: ".o_switch_view.o_kanban.active",
        },
        {
            content: "Switch to list view",
            trigger: ".o_switch_view.o_list",
            run: "click",
        },
        {
            trigger: ".o_switch_view.o_list.active",
        },
        {
            content: "Switch back to kanban",
            trigger: ".o_switch_view.o_kanban",
            run: "click",
        },
        {
            content: "Remove the kanban filter for line2",
            trigger: ".o_kanban_view .o_searchview_facet:nth-child(3) .o_facet_remove",
            run: "click",
        },
        {
            trigger:
                "div.bank_rec_widget_form_amls_list_anchor .o_searchview_facet:nth-child(1) .o_facet_value:contains('INV/2019/00001')",
        },
        {
            content:
                "Nothing has changed: INV/2019/00001 is still selected and contains the search facet",
            trigger:
                "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr.o_rec_widget_list_selected_item td[name='move_id']:contains('INV/2019/00001')",
        },
        // AML Search Facet is removed, and line_ids reset when changing line
        {
            trigger: ".o_bank_rec_st_line:contains('line3')",
        },
        {
            content: "selecting 'line1' should reset the AML search filter ",
            trigger: ".o_bank_rec_st_line:contains('line1')",
            run: "click",
        },
        {
            trigger: "div[name='line_ids'] td[field='name']:contains('line1')",
        },
        {
            content: "select 'line2' again",
            trigger: ".o_bank_rec_st_line:contains('line2')",
            run: "click",
        },
        {
            trigger: "div[name='line_ids'] td[field='name']:contains('line2')",
        },
        {
            content: "Bank Suspense Account is back",
            trigger: "div[name='line_ids'] .o_bank_rec_auto_balance_line",
        },
        {
            content: "AML Search Filter has been reset",
            trigger: ".o_list_view .o_searchview_input_container:not(:has(.o_searchview_facet))",
        },
        // Test statement line selection when using the pager
        {
            content: "Click Pager",
            trigger: ".o_pager_value:first()",
            run: "click",
        },
        {
            content: "Change pager to display lines 1-2",
            trigger: "input.o_pager_value",
            run: "edit 1-2 && click body",
        },
        {
            trigger: ".o_pager_value:contains('1-2')",
        },
        {
            content: "Last St Line is line2",
            trigger: ".o_bank_rec_st_line:last():contains('line2')",
        },
        {
            content: "Page Next",
            trigger: ".o_pager_next:first():not(:disabled)",
            run: "click",
        },
        {
            trigger: ".o_pager_value:contains('3-3')",
        },
        {
            content: "Statement line3 is selected",
            trigger: ".o_bank_rec_selected_st_line:contains('line3')",
        },
        {
            content: "Page to beginning",
            trigger: ".o_pager_next:first()",
            run: "click",
        },
        {
            trigger: "div[name='line_ids'] td[field='name']:contains('line1')",
        },
        {
            content: "Statement line1 is selected",
            trigger: ".o_bank_rec_selected_st_line:contains('line1')",
        },
        // HTML buttons
        {
            content: "Mount an invoice",
            trigger:
                "div.bank_rec_widget_form_amls_list_anchor table.o_list_table td[name='move_id']:contains('INV/2019/00003')",
            run: "click",
        },
        {
            trigger:
                "div[name='line_ids']:has(.text-decoration-line-through:contains('$ 2,000.00'))",
        },
        {
            content: "Select the mounted invoice line and check the strikethrough value",
            trigger:
                "div[name='line_ids'] tr.o_data_row:last() td[field='name']:contains('INV/2019/00003')",
            run: "click",
        },
        {
            trigger: "a.active[name='manual_operations_tab']",
        },
        {
            content: "Fully Paid button",
            trigger: "button[name='action_apply_line_suggestion']:contains('fully paid')",
            run: "click",
        },
        {
            content: "Check the remainder",
            trigger:
                "div[name='line_ids'] tr.o_data_row:contains('Suspense') td[field='debit']:contains('$ 1,000.00')",
        },
        {
            content: "Partial Payment",
            trigger: "button[name='action_apply_line_suggestion']:contains('partial payment')",
            run: "click",
        },
        {
            trigger: "button[name='action_apply_line_suggestion']:contains('fully paid')",
        },
        {
            content: "View Invoice 0003",
            trigger: "button[name='action_redirect_to_move']",
            run: "click",
        },
        {
            trigger: ".o_breadcrumb .active:contains('INV/2019/00003')",
        },
        {
            content: "Breadcrumb back to Bank Reconciliation from INV/2019/00003",
            trigger: ".breadcrumb-item:contains('Bank Reconciliation')",
            run: "click",
        },
        {
            content: "Select the mounted invoice line INV/2019/00003",
            trigger:
                "div[name='line_ids'] tr.o_data_row:last() td[field='name']:contains('INV/2019/00003')",
            run: "click",
        },
        // Match Existing entries tab is activated when line is removed
        {
            trigger: "a.active[name='manual_operations_tab']",
        },
        {
            content: "Remove the invoice",
            trigger: ".o_list_record_remove .fa-trash-o",
            run: "click",
        },
        {
            content: "amls_tab is activated",
            trigger: "a.active[name='amls_tab']",
        },
        {
            content: "Activate Manual Operations to add manual entries",
            trigger: "a[name='manual_operations_tab']",
            run: "click",
        },
        {
            content: "add manual entry 1",
            trigger: "div[name='amount_currency'] input",
            run: "edit -600.0 && click body",
        },
        {
            content: "mount the remaining opening balance line",
            trigger:
                "div[name='line_ids'] tr.o_data_row:contains('Suspense') td[field='credit']:contains('$ 400.00')",
            run: "click",
        },
        {
            trigger: "div[name='amount_currency'] input:value('-400.00'):focus-within",
        },
        {
            content: "Remove the manual entry",
            trigger: ".o_list_record_remove .fa-trash-o",
            run: "click",
        },
        {
            trigger:
                "div[name='line_ids'] tr.o_data_row:contains('Suspense') td[field='credit']:contains('$ 1,000.00')",
        },
        {
            content: "amls_tab is activated and auto balancing line is 1000",
            trigger: "a.active[name='amls_tab']",
        },
        {
            content: "Mount another invoice",
            trigger:
                "div.bank_rec_widget_form_amls_list_anchor table.o_list_table td[name='move_id']:contains('INV/2019/00001')",
            run: "click",
        },
        // After validating, line1 should disappear & line2 should be selected (due to filters)
        {
            trigger:
                "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr.o_rec_widget_list_selected_item td[name='move_id']:contains('INV/2019/00001')",
        },
        {
            content: "Validate line1",
            trigger: "button:contains('Validate')",
            run: "click",
        },
        {
            trigger: "div[name='line_ids'] td[field='name']:contains('line2')",
        },
        {
            content: "The 'line2' is the first kanban record and is selected",
            trigger: ".o_bank_rec_st_line:first():contains('line2')",
        },
        // Test Reset, "Matched" badge and double-click
        {
            content: "Remove the kanban filter for 'Not Matched'",
            trigger: ".o_kanban_view .o_searchview_facet:nth-child(2) .o_facet_remove",
            run: "click",
        },
        {
            trigger: "div[name='line_ids'] td[field='name']:contains('line2')",
        },
        {
            content: "The 'line1' is the first kanban record with line2 selected",
            trigger: ".o_bank_rec_st_line:first():contains('line1')",
        },
        {
            content: "Mount invoice 2 for line 2",
            trigger:
                "div.bank_rec_widget_form_amls_list_anchor table.o_list_table td[name='move_id']:contains('INV/2019/00002')",
            run: "click",
        },
        {
            trigger:
                "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr.o_rec_widget_list_selected_item td[name='move_id']:contains('INV/2019/00002')",
        },
        {
            content: "Validate line2 with double click",
            trigger: "button:contains('Validate')",
            run: "dblclick",
        },
        {
            trigger: ".o_bank_rec_st_line:contains('line2') .badge.text-bg-success",
        },
        {
            content: "Click Pager again after line2 is matched",
            trigger: ".o_pager_value:first()",
            run: "click",
        },
        {
            content: "Change pager to display lines 1-3",
            trigger: "input.o_pager_value",
            run: "edit 1-3 && click body",
        },
        {
            trigger: ".o_bank_rec_selected_st_line:contains('line3')",
        },
        {
            content: "manually select line2 again by clicking it's matched icon",
            trigger: ".badge.text-bg-success:last()",
            run: "click",
        },
        {
            trigger:
                "div[name='line_ids']:not(:has(.fa-trash-o)) td[field='name']:contains('line2')",
        },
        {
            content: "Reset line2",
            trigger: "button:contains('Reset')",
            run: "click",
        },
        {
            trigger: ".o_bank_rec_selected_st_line:contains('line2'):not(:has(div.badge))",
        },
        {
            content: "amls_tab is activated while still on line2 which doesn't contain a badge",
            trigger: ".o_notebook a.active[name='amls_tab']",
        },
        // Test view_switcher
        {
            trigger: ".o_switch_view.o_kanban.active",
        },
        {
            content: "Switch to list view",
            trigger: ".o_switch_view.o_list",
            run: "click",
        },
        {
            trigger: ".btn-secondary:contains('View')",
        },
        {
            content: "Select the first Match Button (line2)",
            trigger: ".btn-secondary:contains('Match')",
            run: "click",
        },
        {
            trigger: ".o_bank_rec_st_line:last():contains('line2')",
        },
        {
            content: "Last St Line is line2",
            trigger: ".o_bank_rec_selected_st_line:contains('line2')",
            run: "click",
        },
        {
            content: "Button To Check will reconcile since partner is saved on line2",
            trigger: ".btn-secondary:contains('To Check')",
            run: "click",
        },
        {
            trigger:
                ".o_bank_rec_selected_st_line:contains('line2'):has(div.badge[title='Matched'] i):has(span.badge:contains('To check'))",
        },
        {
            content: "both badges are visible, trash icon is not, manual operation tab is active",
            trigger:
                "div[name='line_ids']:not(:has(.fa-trash-o))+.o_notebook a.active[name='manual_operations_tab']",
        },
        {
            trigger: ".o_switch_view.o_kanban.active",
        },
        {
            content: "Switch to list view",
            trigger: ".o_switch_view.o_list",
            run: "click",
        },
        {
            trigger: ".o_switch_view.o_list.active",
        },
        {
            content: "Remove the line filter",
            trigger: ".o_searchview_facet:contains('0002') .o_facet_remove",
            run: "click",
        },
        {
            trigger: ".o_data_row:contains('line2'):has(.btn-secondary:contains('View'))",
        },
        {
            content: "Select the first Match Button (line3)",
            trigger: ".btn-secondary:contains('Match')",
            run: "click",
        },
        {
            trigger: ".o_bank_rec_stats_buttons",
        },
        {
            content: "Open search bar menu",
            trigger: ".o_searchview_dropdown_toggler:eq(0)",
            run: "click",
        },
        // Test Reco Model
        {
            trigger: ".o-dropdown--menu.o_search_bar_menu",
        },
        {
            content: "Choose a filter",
            trigger: ".o_search_bar_menu .dropdown-item:first()",
            run: "click",
        },
        {
            trigger: ".o-dropdown--menu",
        },
        {
            content: "Not Matched Filter",
            trigger: ".dropdown-item:contains('Not Matched')",
            run: "click",
        },
        {
            trigger: ".o_switch_view.o_kanban.active",
        },
        {
            content: "reco model dropdown",
            trigger: ".bank_rec_reco_model_dropdown i",
            run: "click",
        },
        {
            trigger: ".o-dropdown--menu",
        },
        {
            content: "create model",
            trigger: ".dropdown-item:contains('Create model')",
            run: "click",
        },
        {
            content: "model name",
            trigger: "input#name_0",
            run: "edit Bank Fees",
        },
        {
            content: "add an account",
            trigger: "a:contains('Add a line')",
            run: "click",
        },
        {
            content: "search for bank fees account",
            trigger: "[name='account_id'] input",
            run: "edit Bank Fees",
        },
        {
            trigger: ".o-autocomplete--dropdown-menu",
        },
        {
            content: "select the bank fees account",
            trigger: ".o-autocomplete--dropdown-item:contains('Bank Fees')",
            run: "click",
        },
        {
            trigger: ".o_breadcrumb .active > span:contains('New')",
        },
        {
            content: "Breadcrumb back to Bank Reconciliation from the model",
            trigger: ".breadcrumb-item:contains('Bank Reconciliation')",
            run: "click",
        },
        {
            content: "Choose Bank Fees Model",
            trigger: ".recon_model_button:contains('Bank Fees')",
            run: "click",
        },
        {
            content: "Validate line3",
            trigger: "button:contains('Validate').btn-primary",
            run: "dblclick",
        },
        {
            trigger: ".o_reward_rainbow_man",
        },
        {
            content:
                "Remove the kanbans 'not matched' filter to reset all lines - use the rainbow man button",
            trigger: "p.btn-primary:contains('All Transactions')",
            run: "click",
        },
        {
            trigger:
                ".o_kanban_view .o_searchview:first() .o_searchview_facet:last():contains('Bank')",
        },
        {
            content: "Wait for search model change and line3 to appear",
            trigger: ".o_bank_rec_st_line:last():contains('line3')",
        },
        {
            trigger: ".o_bank_rec_selected_st_line:contains('line2')",
        },
        {
            content: "'line2' should be selected, reset it",
            trigger: "button:contains('Reset')",
            run: "click",
        },
        {
            trigger: ".o_bank_rec_st_line:contains('line2'):not(:has(div.badge))",
        },
        {
            content: "select matched 'line3'",
            trigger: ".o_bank_rec_st_line:contains('line3')",
            run: "click",
        },
        {
            trigger: ".o_bank_rec_selected_st_line:contains('line3')",
        },
        {
            content: "'line3' should be selected, reset it",
            trigger: "button:contains('Reset')",
            run: "click",
        },
        {
            trigger: ".o_bank_rec_st_line:contains('line3'):not(:has(div.badge))",
        },
        {
            content: "select matched 'line1'",
            trigger: ".o_bank_rec_st_line:contains('line1')",
            run: "click",
        },
        {
            trigger: ".o_bank_rec_selected_st_line:contains('line1')",
        },
        {
            content: "'line1' should be selected, reset it",
            trigger: "button:contains('Reset')",
            run: "click",
        },
        {
            trigger: ".o_bank_rec_stats_buttons",
        },
        {
            content: "Open search bar menu",
            trigger: ".o_searchview_dropdown_toggler:eq(0)",
            run: "click",
        },
        {
            trigger: "button:contains('Validate')",
        },
        {
            content: "Filter Menu",
            trigger: ".o_search_bar_menu .dropdown-item:first()",
            run: "click",
        },
        {
            trigger: ".o-dropdown--menu",
        },
        {
            content: "Activate the Not Matched filter",
            trigger: ".dropdown-item:contains('Not Matched')",
            run: "click",
        },
        {
            trigger: ".o_searchview_facet:contains('Not Matched')",
        },
        {
            content: "Close the Filter Menu",
            trigger: ".o_searchview_dropdown_toggler:eq(0)",
            run: "click",
        },
        {
            trigger: ".o_searchview_facet:contains('Not Matched')",
        },
        {
            content: "select 'line2'",
            trigger: ".o_bank_rec_st_line:contains('line2')",
            run: "click",
        },
        {
            trigger: ".o_bank_rec_selected_st_line:contains('line2')",
        },
        {
            content: "Validate 'line2' again",
            trigger: "button:contains('Validate')",
            run: "click",
        },
        {
            trigger: ".o_bank_rec_selected_st_line:contains('line3')",
        },
        {
            content: "'line3' should be selected now",
            trigger: ".o_bank_rec_selected_st_line:contains('line3')",
        },
        // Test the Balance when changing journal and liquidity line
        ...stepUtils.toggleHomeMenu(),
        ...accountTourSteps.goToAccountMenu("Reset back to accounting module"),
        {
            trigger: ".o_breadcrumb",
        },
        {
            content: "Open the bank reconciliation widget for Bank2",
            trigger: "button.btn-secondary[name='action_open_reconcile']:last()",
            run: "click",
        },
        {
            content: "Remove the kanbans 'not matched' filter",
            trigger: ".o_kanban_view .o_searchview_facet:nth-child(2) .o_facet_remove",
            run: "click",
        },
        {
            content: "Remove the kanban 'journal' filter",
            trigger: ".o_kanban_view .o_searchview_facet:nth-child(1) .o_facet_remove",
            run: "click",
        },
        {
            content: "select 'line1' from another journal",
            trigger: ".o_bank_rec_st_line:contains('line1')",
            run: "click",
        },
        ...accountTourSteps.bankRecUiReportSteps(),
        {
            content: "select 'line4' from this journal",
            trigger: ".o_bank_rec_st_line:contains('line4')",
            run: "click",
        },
        {
            trigger: ".o_bank_rec_selected_st_line:contains('line4')",
        },
        {
            content: "balance is $222.22",
            trigger: ".btn-link:contains('$ 222.22')",
        },
        {
            content: "Select the liquidity line",
            trigger: "tr.o_bank_rec_liquidity_line td[field='debit']",
            run: "click",
        },
        {
            trigger: "div[name='amount_currency'] input:focus-within",
        },
        {
            content: "Modify the liquidity line amount",
            trigger: "div[name='amount_currency'] input",
            run: "edit -333.33 && click body",
        },
        {
            trigger: ".btn-link:contains('$ -333.33')",
        },
        {
            content: "balance displays $-333.33",
            trigger: ".btn-link:contains('$ -333.33')",
        },
        {
            content: "Modify the label",
            trigger: "div[name='name'] input",
            run: "edit Spontaneous Combustion && click body",
        },
        {
            content: "statement line displays combustion and $-333.33",
            trigger: ".o_bank_rec_selected_st_line:contains('Combustion'):contains('$ -333.33')",
        },
        // Test that changing the balance in the list view updates the right side of the kanban view
        // (including reapplying matching rules)
        {
            content: "select matched 'line2'",
            trigger: ".o_bank_rec_st_line:contains('line2')",
            run: "click",
        },
        {
            trigger: ".o_bank_rec_selected_st_line:contains('line2')",
        },
        {
            content: "'line2' should be selected, reset it",
            trigger: "button:contains('Reset')",
            run: "click",
        },
        {
            trigger: ".o_bank_rec_selected_st_line:contains('line2'):not(:has(div.badge))",
        },
        {
            content: "Liquidity line displays debit '$ 100.00'",
            trigger:
                "div[name='line_ids'] table.o_list_table tr.o_bank_rec_liquidity_line td[field='debit']:contains('$ 100.00')",
        },
        {
            trigger: ".o_switch_view.o_kanban.active",
        },
        {
            content: "Switch to list view",
            trigger: ".o_switch_view.o_list",
            run: "click",
        },
        {
            content: "Click amount field of 'line2'; Selects the row",
            trigger: "table.o_list_table tr.o_data_row:contains('line2') td[name='amount']",
            run: "click",
        },
        {
            content: "Set balance of 'line2' (selected row) to 500.00",
            trigger: "table.o_list_table tr.o_data_row.o_selected_row td[name='amount'] input",
            run: "edit 500.00 && click body",
        },
        {
            trigger: ".o_switch_view.o_list.active",
        },
        {
            content: "Switch back to kanban",
            trigger: ".o_switch_view.o_kanban",
            run: "click",
        },
        {
            content: "'line2' is still selected",
            trigger: ".o_bank_rec_st_line:contains('line2')",
        },
        {
            content: "Liquidity line displays debit '$ 500.00'",
            trigger:
                "div[name='line_ids'] table.o_list_table tr.o_bank_rec_liquidity_line td[field='debit']:contains('$ 500.00')",
        },
        {
            content:
                "'INV/2019/00001' has been selected as matching existing entry by matching rules",
            trigger:
                "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr.o_rec_widget_list_selected_item td[name='name']:contains('INV/2019/00001')",
        },
        // End
        ...stepUtils.toggleHomeMenu(),
        ...accountTourSteps.goToAccountMenu("Reset back to accounting module"),
        {
            content: "check that we're back on the dashboard",
            trigger: 'a:contains("Customer Invoices")',
        },
    ],
});

registry.category("web_tour.tours").add('account_accountant_bank_rec_widget_reconciliation_button',
    {
        url: '/odoo',
        steps: () => [
        stepUtils.showAppsMenuItem(),
        ...accountTourSteps.goToAccountMenu("Open the accounting module"),
        {
            content: "Open the bank reconciliation widget",
            trigger: "button.btn-secondary[name='action_open_reconcile']",
            run: "click",
        },
        {
            content: "Remove suggested line, if present",
            trigger: ".o_list_record_remove",
            run() {
                const button = document.querySelector('.fa-trash-o');
                if(button) {
                    button.click();
                }
            }
        },
        {
            content: "Wait for deletion",
            trigger: ".o_data_row:contains('Open balance')",
        },
        {
            content: "Select reconciliation model creating a new move",
            trigger: ".recon_model_button:contains('test reconcile')",
            run: "click",
        },
        {
            content: "Confirm move created through reconciliation model writeoff button",
            trigger: "button[name=action_post]",
            run: "click",
        },
        {
            trigger: ".o_breadcrumb",
        },
        {
            content: "Breadcrumb back to Bank Reconciliation from created move",
            trigger: ".breadcrumb-item:contains('Bank Reconciliation')",
            run: "click",
        },
        {
            content: "Validate created move added as a line in reco widget",
            trigger: "button:contains('Validate')",
            run: "click",
        },
        // End
        ...stepUtils.toggleHomeMenu(),
        ...accountTourSteps.goToAccountMenu("Reset back to accounting module"),
        {
            content: "check that we're back on the dashboard",
            trigger: 'a:contains("Customer Invoices")',
        },
    ],
});
