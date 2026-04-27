/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import { accountTourSteps } from "@account/js/tours/account";

registry.category("web_tour.tours").add('account_accountant_bank_rec_widget_statements',
    {
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
            content: "Statement button",
            trigger:
                ".o_bank_rec_st_line:eq(2) a.oe_kanban_action:contains('Statement'):not(:visible)",
            run: "click",
        },
        {
            trigger: ".modal-dialog:contains('Create Statement')",
        },
        {
            content: "Save the statement with proposed values",
            trigger: ".o_form_button_save",
            run: "click",
        },
        {
            content: "Click the Valid Statement with $ 1,000.00 that is visible in Kanban",
            trigger: "span[name='kanban-subline-clickable-amount']:contains('$ 1,000.00')",
            run: "click",
        },
        {
            content: "Modify the end balance",
            trigger: "input[id='balance_end_real_0']",
            run: "edit 100 && click body",
        },
        {
            trigger: ".alert-warning:contains('The running balance')",
        },
        {
            content: "Dialog displays warning, save anyway",
            trigger: ".breadcrumb-item.o_back_button:nth-of-type(2)",
            run: "click",
        },
        {
            trigger: ".btn-link:contains('$ 2,100.00')",
        },
        {
            content: "Click the red statement, after checking the balance",
            trigger: "span[name='kanban-subline-clickable-amount']:contains('$ 100.00')",
            run: "click",
        },
        {
            content: "Back in the form view",
            trigger: ".alert-warning:contains('The running balance')",
        },
        {
            content: "Click on Action",
            trigger: ".o_cp_action_menus button",
            run: "click",
        },
        {
            content: "Click on Delete",
            trigger: ".o-dropdown--menu span:contains('Delete')",
            run: "click",
        },
        {
            content: "Confirm Deletion",
            trigger: ".btn-primary:contains('Delete')",
            run: "click",
        },
        {
            trigger: ".o_kanban_renderer:not(:has(.kanban-statement))",
        },
        {
            content: "balance displays $3000.00 and no statement",
            trigger: ".btn-link:contains('$ 3,000')",
        },
        // End
        ...stepUtils.toggleHomeMenu(),
        ...accountTourSteps.goToAccountMenu("Reset back to accounting module"),
        {
            content: "check that we're back on the dashboard",
            trigger: 'a:contains("Customer Invoices")',
        }
    ]
});
