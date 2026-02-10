import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("version_timeline_auto_save_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Open Employees app",
            trigger: ".o_app[data-menu-xmlid='hr.menu_hr_root']",
            run: "click",
        },
        {
            content: "Open an Employee Profile",
            trigger: ".o_kanban_record:contains('Bob M.')",
            run: "click",
        },
        {
            content: "Open Payroll Page",
            trigger: ".o_notebook_headers a[name='payroll_information']",
            run: "click",
        },
        {
            content: "Open contract end date",
            trigger: ".o_field_widget[name='contract_date_end'] .o_input",
            run: "click",
        },
        {
            content: "Go to the next month",
            trigger: ".o_next",
            run: "click",
        },
        {
            content: "Choose date X + 1",
            trigger: ".o_date_item_cell:nth-child(11) > div",
            run: "click",
        },
        {
            content: "Open Create New Version",
            trigger: ".o_field_widget[name='version_id'] > .o_arrow_button_wrapper > button",
            run: "click",
        },
        {
            content: "Go to the next month",
            trigger: ".o_next",
            run: "click",
        },
        {
            content: "Choose date X + 2",
            trigger: ".o_date_item_cell:nth-child(12) > div",
            run: "click",
        },
        {
            content: "Wait until the form is saved",
            trigger: "body .o_form_saved",
        },
    ],
});
