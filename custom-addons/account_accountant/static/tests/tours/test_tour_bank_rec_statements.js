/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('account_accountant_bank_rec_widget_statements',
    {
        test: true,
        url: '/web',
        steps: () => [
        stepUtils.showAppsMenuItem(),
        ...stepUtils.goToAppSteps('account_accountant.menu_accounting', "Open the accounting module"),
        {
            content: "Open the bank reconciliation widget",
            extra_trigger: ".o_breadcrumb",
            trigger: "button.btn-primary[name='action_open_reconcile']",
        },
        {
            content: "Statement button",
            trigger: ".o_bank_rec_st_line:eq(2) .oe_kanban_action_a:contains('Statement')",
            allowInvisible: true,
        },
        {
            content: "Save the statement with proposed values",
            extra_trigger: ".modal-dialog:contains('Create Statement')",
            trigger: ".o_form_button_save",
        },
        {
            content: "Click the Valid Statement with $ 1,000.00 that is visible in Kanban",
            trigger: "span[name='kanban-subline-clickable-amount']:contains('$ 1,000.00')",
        },
        {
            content: "Modify the end balance",
            trigger: "input[id='balance_end_real_0']",
            run: "text 100",
        },
        {
            content: "Dialog displays warning, save anyway",
            extra_trigger: ".modal-body div.alert-warning:contains('The running balance')",
            trigger: ".modal-dialog .btn-primary[special='save']",
        },
        {
            content: "Click the red statement, after checking the balance",
            extra_trigger: ".btn-link:contains('$ 2,100.00')",
            trigger: "span[name='kanban-subline-clickable-amount']:contains('$ 100.00')",
        },
        {
            content: "Delete the statement",
            trigger: ".modal-dialog .btn-danger:contains('Delete')",
        },
        {
            content: "Confirm Deletion",
            extra_trigger: ".modal-dialog:contains('Confirmation')",
            trigger: ".btn-primary:contains('Ok')",
        },
        {
            content: "balance displays $3000.00 and no statement",
            extra_trigger: ".o_kanban_renderer:not(:has(.kanban-statement))",
            trigger: ".btn-link:contains('$ 3,000')",
            isCheck: true,
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
