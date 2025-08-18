import { registry } from '@web/core/registry';
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("time_off_allocation_warning_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Click Time Off",
            trigger: ".o_app[data-menu-xmlid='hr_holidays.menu_hr_holidays_root']",
            run: "click",
        },
        {
            content: "Open Management menu",
            trigger: ".o-dropdown[data-menu-xmlid='hr_holidays.menu_hr_holidays_management']",
            run: "click",
        },
        {
            content: "Go to Allocations",
            trigger: ".o-dropdown-item[data-menu-xmlid='hr_holidays.hr_holidays_menu_manager_approve_allocations']",
            run: "click",
        },
        {
            content: "Create a new allocation",
            trigger: ".o-kanban-button-new",
            run: "click",
        },
        {
            content: "Click to select a leave type",
            trigger: ".o_field_widget[name='holiday_status_id'] .o-autocomplete--input",
            run: "click",
        },
        {
            trigger: ".o-autocomplete--dropdown-item:nth-child(1) > a",
            run: "click",
        },
        {
            content: "Open the start date picker",
            trigger: ".o_field_widget[name='date_from'] .o_input",
            run: "click",
        },
        {
            content: "Choose a start date",
            trigger: ".o_date_item_cell:nth-child(15) > div",
            run: "click",
        },
        {
            content: "Open the end date picker",
            trigger: ".o_field_widget[name='date_to'] .o_input",
            run: "click",
        },
        {
            content: "Choose a future end date",
            trigger: ".o_date_item_cell:nth-child(22) > div",
            run: "click",
        },
        ...stepUtils.saveForm(),
        {
            trigger: ".o_menu_brand",
            run: "click",
        },
    ],
});
