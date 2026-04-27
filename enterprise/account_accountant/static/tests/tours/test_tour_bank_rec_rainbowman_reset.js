/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import { accountTourSteps } from "@account/js/tours/account";

registry.category("web_tour.tours").add("account_accountant_bank_rec_widget_rainbowman_reset", {
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
        // Rainbowman gets reset
        {
            content: "Mount invoice 2 for line 1",
            trigger:
                "div.bank_rec_widget_form_amls_list_anchor table.o_list_table td[name='move_id']:contains('INV/2019/00002')",
            run: "click",
        },
        {
            trigger:
                "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr.o_rec_widget_list_selected_item td[name='move_id']:contains('INV/2019/00002')",
        },
        {
            content: "Validate line1",
            trigger: "button:contains('Validate')",
            run: "click",
        },
        {
            trigger: ".o_bank_rec_selected_st_line:contains('line2')",
        },
        {
            content: "No records brings rainbows",
            trigger: "div.o_kanban_view .o_searchview_input",
            run: "fill thisShouldNotReturnAnyRecords",
        },
        {
            content: "Select the Journal Entry search option from the dropdown",
            trigger: ".o_searchview_autocomplete li:contains(Journal Entry)",
            run: "click",
        },
        {
            trigger: ".o_reward_rainbow_man:contains('You reconciled 1 transaction in')",
        },
        {
            content: "Remove the filter while rainbow man is on screen",
            trigger: ".o_kanban_view .o_searchview_facet:nth-child(3) .o_facet_remove",
            run: "click",
        },
        {
            trigger: ".o_bank_rec_st_line:contains('line2')",
        },
        {
            content: "Search for no results again",
            trigger: "div.o_kanban_view .o_searchview_input",
            run: "fill thisShouldNotReturnAnyRecords",
        },
        {
            content: "Select the Journal Entry search option from the dropdown",
            trigger: ".o_searchview_autocomplete li:contains(Journal Entry)",
            run: "click",
        },
        {
            content: "No content helper is displayed instead of rainbowman",
            trigger: ".o_view_nocontent_smiling_face",
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
