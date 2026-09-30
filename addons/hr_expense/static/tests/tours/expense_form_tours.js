import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add('create_expense_no_employee_access_tour', {
    url: "/odoo",
    steps: () => [
    ...stepUtils.goToAppSteps('hr_expense.menu_hr_expense_root', "Go to the Expenses app"),
    {
        content: "Remove filter for own expenses",
        trigger: '.o_facet_value:contains(My Expenses) + button[title="Remove"]',
        run: 'click',
    },
    {
        content: "Go to form view of pre-prepared record",
        trigger: '.o_data_cell:contains(expense_for_tour_0)',
        run: 'click',
    },
    {
        content: "Click employee selection dropdown",
        trigger: 'input#employee_id_0',
        run: 'click',
    },
    {
        content: "Delete default search",
        trigger: 'input#employee_id_0',
        run: "clear",
    },
    {
        content: "Select test expense employee",
        trigger: 'a.dropdown-item:contains(expense_employee)',
        run: 'click',
    },
    {
        content: "Save",
        trigger: ".o_form_button_save:enabled",
        run: 'click',
    },
    {
        content: "wait until the form is saved",
        trigger: "body .o_form_saved",
    },
    {
        content: "Exit form",
        trigger: '.o_menu_brand',
        run: 'click',
    },
    stepUtils.showAppsMenuItem(),
    {
        content: "Check",
        trigger: '.o_app[data-menu-xmlid="hr_expense.menu_hr_expense_root"]',
    },
]});

registry.category("web_tour.tours").add("do_not_create_zero_amount_expense", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps("hr_expense.menu_hr_expense_root", "Go to the Expenses app"),
        {
            content: "Remove filter for own expenses",
            trigger: '.o_facet_value:contains(My Expenses) + button[title="Remove"]',
            run: 'click',
        },
        {
            content: "Go to an expense",
            trigger: '.o_data_row .o_data_cell[data-tooltip="expense_for_tour"]',
            run: "click",
        },
        {
            content: "Select category to Expense",
            trigger: "div[name=product_id] input",
            run: "click",
        },
        {
            content: "Choose category to Expense",
            trigger:
                ".o_field_widget[name=product_id] .o-autocomplete--dropdown-menu li:contains(EXP_GEN)",
            run: "click",
        },
        {
            content: "Set total amount to zero",
            trigger: "div[name=total_amount_currency] input",
            run: "edit 0.0",
        },
        {
            content: "Click Submit",
            trigger: ".o_expense_submit",
            run: "click",
        },
        {
            content: "Close the displayed user error indicating that the expense total cannot be set to zero if non-draft.",
            trigger: ".modal .modal-footer .btn-primary.o-default-button",
            run: "click",
        },
        {
            content: "Set total amount to ten",
            trigger: "div[name=total_amount_currency] input",
            run: "edit 10.0",
        },
        {
            content: "Click Submit",
            trigger: ".o_expense_submit",
            run: "click",
        },
        // Valid expense was saved on submit
        {
            content: "Set total amount to zero",
            trigger: "div[name=total_amount_currency] input",
            run: "edit 0.0",
        },
        // Save should fail
        {
            content: "Click Approve",
            trigger: ".o_expense_approve",
            run: "click",
        },
        {
            content: "Close the displayed user error indicating that the expense total cannot be set to zero if non-draft.",
            trigger: ".modal .modal-footer .btn-primary.o-default-button",
            run: "click",
        },
        // Return to the valid expense
        ...stepUtils.discardForm(),
    ],
});
