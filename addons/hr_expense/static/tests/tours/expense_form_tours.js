/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('create_expense_no_employee_access_tour', {
    test: true,
    url: "/web",
    steps: () => [
    ...stepUtils.goToAppSteps('hr_expense.menu_hr_expense_root', "Go to the Expenses app"),
    {
        content: "Remove filter for own expenses",
        trigger: '.o_facet_value:contains(My Expense) + button[title="Remove"]',
    },
    {
        content: "Go to form view of pre-prepared record",
        trigger: '.o_data_cell:contains(expense_for_tour_0)'
    },
    {
        content: "Click employee selection dropdown",
        trigger: 'input#employee_id_0',
    },
    {
        content: "Delete default search",
        trigger: 'input#employee_id_0',
        run() {
            const dropdown = document.querySelector('input#employee_id_0');
            dropdown.value = '';
        }
    },
    {
        content: "Select test expense employee",
        trigger: 'a.dropdown-item:contains(expense_employee)',
    },
    {
        content: "Save",
        trigger: '.o_form_button_save',
    },
    {
        content: "Exit form",
        trigger: '.o_menu_brand',
    },
    stepUtils.showAppsMenuItem(),
    {
        content: "Check",
        trigger: '.o_app[data-menu-xmlid="hr_expense.menu_hr_expense_root"]',
        isCheck: true,
    },
]});
