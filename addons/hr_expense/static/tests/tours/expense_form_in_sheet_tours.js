/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add("do_not_create_zero_amount_expense_in_sheet", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps("hr_expense.menu_hr_expense_root", "Go to the Expenses app"),
        {
            content: "Go to Expense Reports",
            trigger: '.dropdown-item[data-menu-xmlid="hr_expense.menu_hr_expense_report"]',
            run: "click",
        },
        {
            content: "Go to a report",
            trigger: '.o_data_row .o_data_cell[data-tooltip="report_for_tour"]',
            run: "click",
        },
        {
            content: "Add an expense line",
            trigger: 'div[name="expense_line_ids"] .o_field_x2many_list_row_add a',
            run: "click",
        },
        {
            content: "Create new expense line",
            trigger: ".modal .modal-footer .o_create_button",
            run: "click",
        },
        {
            content: "Add expense name",
            trigger: ".modal .modal-body .o_field_widget[name=name] input",
            run: "edit expense_for_tour",
        },
        {
            content: "Set total amount to zero",
            trigger: ".modal .modal-body .o_field_widget[name=total_amount_currency] input",
            run: "edit 0.0",
        },
        {
            content: "Select category to Expense",
            trigger: ".modal .modal-body .o_field_widget[name=product_id] input",
            run: "click",
        },
        {
            content: "Choose category to Expense",
            trigger:
                ".o_field_widget[name=product_id] .o-autocomplete--dropdown-menu li:contains([EXP_GEN])",
            run: "click",
        },
        {
            content: "Click Save",
            trigger: ".modal .modal-footer .o_form_button_save",
            run: "click",
        },
        {
            content:
                "Close the displayed user error indicating that the expense total cannot be set to zero if it is linked to a report.",
            trigger: ".modal .modal-footer .btn-primary.o-default-button",
            run: "click",
        },
        {
            content: "Set total amount to ten",
            trigger: ".modal .modal-body .o_field_widget[name=total_amount_currency] input",
            run: "edit 10.0",
        },
        {
            content: "Click Save",
            trigger: ".modal .modal-footer .o_form_button_save",
            run: "click",
        },
        {
            content: "Wait the modal is closed",
            trigger: "body:not(:has(.modal))",
        },
        // Save the report
        ...stepUtils.saveForm(),
    ],
});
