/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('account_accountant_bank_rec_widget_rainbowman_reset',
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
            content: "'line1' should be selected and form mounted",
            extra_trigger: "div[name='line_ids'] td[field='name']:contains('line1')",
            trigger: ".o_bank_rec_selected_st_line:contains('line1')",
            run: () => {},
        },
        // Rainbowman gets reset
        {
            content: "Mount invoice 2 for line 1",
            trigger: "div.bank_rec_widget_form_amls_list_anchor table.o_list_table td[name='move_id']:contains('INV/2019/00002')",
        },
        {
            content: "Validate line1",
            extra_trigger: "div.bank_rec_widget_form_amls_list_anchor table.o_list_table tr.o_rec_widget_list_selected_item td[name='move_id']:contains('INV/2019/00002')",
            trigger: "button:contains('Validate')",
        },
        {
            content: "No records brings rainbows",
            extra_trigger: ".o_bank_rec_selected_st_line:contains('line2')",
            trigger: "div.o_kanban_view .o_searchview_input",
            run: "text thisShouldNotReturnAnyRecords",
        },
        {
            content: "Select the Journal Entry search option from the dropdown",
            trigger: ".o_searchview_autocomplete li:contains(Journal Entry)",
        },
        {
            content: "Remove the filter while rainbow man is on screen",
            extra_trigger: ".o_reward_rainbow_man:contains('You reconciled 1 transaction in')",
            trigger: ".o_kanban_view .o_searchview_facet:nth-child(3) .o_facet_remove",
        },
        {
            content: "Search for no results again",
            extra_trigger: ".o_bank_rec_st_line:contains('line2')",
            trigger: "div.o_kanban_view .o_searchview_input",
            run: "text thisShouldNotReturnAnyRecords",
        },
        {
            content: "Select the Journal Entry search option from the dropdown",
            trigger: ".o_searchview_autocomplete li:contains(Journal Entry)",
        },
        {
            content: "No content helper is displayed instead of rainbowman",
            trigger: ".o_view_nocontent_smiling_face",
            run: () => {},
        },
        // End
        stepUtils.toggleHomeMenu(),
        ...stepUtils.goToAppSteps(
            'account_accountant.menu_accounting',
            "Reset back to accounting module"
        ),
        {
            content: "check that we're back on the dashboard",
            trigger: 'a:contains("Customer Invoices")',
            run() {},
        }
    ]
});
