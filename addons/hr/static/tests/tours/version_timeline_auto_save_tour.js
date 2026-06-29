import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("version_timeline_auto_save_tour", {
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Open Employees app",
            trigger: ".o_app[data-menu-xmlid='hr.menu_hr_root']",
            run: "click",
        },
        {
            content: "Open Management menu",
            trigger: '[data-menu-xmlid="hr.menu_hr_employee_payroll"]',
            run: "click",
        },
        {
            content: "Open an Employee Profile",
            trigger: ".o_kanban_record:contains('Bob M.')",
            run: "click",
        },
        {
            content: "Open Payroll Page",
            trigger: ".o_notebook_headers button[name='payroll_information']",
            run: "click",
        },
        {
            content: "Version should have no contract",
            trigger: ".o_arrow_button_wrapper[data-tooltip='No contract']",
        },
        {
            content: "Set a contract date start on the version",
            trigger: ".o_field_widget[name='contract_date_start'] .o_input",
            run: "click",
        },
        {
            content: "Choose date X + 1",
            trigger: ".o_datetime_picker .o_date_item_cell:nth-child(11) > div",
            run: "click",
        },
        {
            trigger: "body:not(:has(.o_datetime_picker))",
        },
        ...stepUtils.saveForm(),
        {
            content: "Tooltip should now reflect the new contract date start",
            trigger: ".o_arrow_button_wrapper[data-tooltip^='Employee:']",
        },
        {
            content: "Open contract end date",
            trigger: ".o_field_widget[name='contract_date_end'] .o_input",
            run: "click",
        },
        {
            content: "Choose date X + 2",
            trigger: ".o_datetime_picker .o_date_item_cell:nth-child(12) > div",
            run: "click",
        },
        {
            trigger: "body:not(:has(.o_datetime_picker))",
        },
        {
            content: "Wait the form is dirty and click on save button",
            trigger: "body:has(.o_form_dirty) .o_form_button_save",
            run: "click",
        },
        {
            content: "Close the End of Contract dialog ('Correct terms' button)",
            trigger: ".modal button.btn-primary",
            run: "click",
        },
        {
            content: "Open Create New Version",
            trigger: ".o_field_widget[name='version_id'] > .o_arrow_button_wrapper > button",
            run: "click",
        },
        {
            content: "Choose date X + 3",
            trigger: ".o_datetime_picker .o_date_item_cell:nth-child(13) > div",
            run: "click",
        },
        {
            trigger: "body:not(:has(.o_datetime_picker))",
        },
        {
            content: "Wait until new version is created and form reloads",
            trigger: "body .o_form_saved",
        },
    ],
});
